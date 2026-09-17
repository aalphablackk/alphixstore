import uuid
from datetime import timedelta

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from orders.services import release_order_stock
from .models import Payment
from .paystack import initialize_transaction
from orders.email_service import send_payment_confirmation_email


# ============================================================
# PAYMENT CONFIGURATION
# ============================================================

PAYMENT_EXPIRATION_MINUTES = 30


# ============================================================
# PAYMENT REFERENCE
# ============================================================

def generate_payment_reference():
    """
    Generate a unique internal payment reference.
    """

    return f"ALPHIX-{uuid.uuid4().hex[:12].upper()}"


# ============================================================
# INITIALIZE PAYMENT
# ============================================================

def initialize_payment(*, order, request):
    """
    Create a Payment record and initialize the transaction
    with Paystack.

    The Payment record starts as PENDING.

    If Paystack initialization fails, the Payment is immediately
    marked as FAILED so we never leave a fake PENDING payment
    behind.
    """

    reference = generate_payment_reference()

    payment = Payment.objects.create(
        order=order,
        payment_reference=reference,
        amount=order.total_amount,
        currency="NGN",
        provider=Payment.Provider.PAYSTACK,
        status=Payment.Status.PENDING,
        expires_at=(
            timezone.now()
            + timedelta(minutes=PAYMENT_EXPIRATION_MINUTES)
        ),
    )

    callback_url = request.build_absolute_uri(
        reverse("payment_callback")
    )

    try:

        response = initialize_transaction(
            email=order.user.email,
            amount=payment.amount,
            reference=payment.payment_reference,
            callback_url=callback_url,
            metadata={
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            },
        )

    except Exception:
        """
        Paystack initialization failed.

        Do not leave this Payment as PENDING.
        """

        payment.status = Payment.Status.FAILED

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise

    authorization_url = response.get(
        "authorization_url"
    )

    if not authorization_url:

        payment.status = Payment.Status.FAILED

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise ValueError(
            "Paystack did not return a payment authorization URL."
        )

    return payment, response


# ============================================================
# FAIL PAYMENT
# ============================================================

def fail_payment(payment):
    """
    Mark a pending payment as FAILED and release the stock
    reserved for its order.

    Safe to call multiple times.

    Returns:
        True  -> payment was changed
        False -> payment was already processed
    """

    with transaction.atomic():

        locked_payment = (
            Payment.objects
            .select_for_update()
            .select_related("order")
            .get(pk=payment.pk)
        )

        # --------------------------------------------
        # Payment already processed
        # --------------------------------------------

        if locked_payment.status != Payment.Status.PENDING:
            return False

        locked_payment.status = Payment.Status.FAILED

        locked_payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        order = locked_payment.order

        # --------------------------------------------
        # Do not alter an already-paid order
        # --------------------------------------------

        if order.payment_status == "PAID":
            return True

        # --------------------------------------------
        # Mark order payment as failed
        # --------------------------------------------

        order.payment_status = "FAILED"

        order.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )

        # --------------------------------------------
        # Release reserved stock
        # --------------------------------------------

        release_order_stock(order)

        return True


# ============================================================
# CONFIRM PAYMENT
# ============================================================

def confirm_payment(
    *,
    payment,
    transaction_data,
):
    """
    Confirm a successful Paystack payment.

    The Payment and Order are locked to prevent the callback
    and webhook from successfully processing the same payment
    at the same time.

    Returns:
        True  -> payment confirmed
        False -> payment could not be confirmed because it was
                 already processed or is no longer pending
    """

    transaction_reference = (
        transaction_data.get("id")
        or transaction_data.get("reference")
    )

    with transaction.atomic():

        locked_payment = (
            Payment.objects
            .select_for_update()
            .select_related("order")
            .get(pk=payment.pk)
        )

        # --------------------------------------------
        # Already successfully processed
        # --------------------------------------------

        if (
            locked_payment.status
            == Payment.Status.SUCCESSFUL
        ):

            return True

        # --------------------------------------------
        # Payment was already failed/expired/etc.
        # --------------------------------------------

        if (
            locked_payment.status
            != Payment.Status.PENDING
        ):

            return False

        # --------------------------------------------
        # Confirm Payment
        # --------------------------------------------

        locked_payment.status = (
            Payment.Status.SUCCESSFUL
        )

        locked_payment.transaction_reference = (
            str(transaction_reference)
            if transaction_reference
            else None
        )

        locked_payment.save(
            update_fields=[
                "status",
                "transaction_reference",
                "updated_at",
            ]
        )

        # --------------------------------------------
        # Confirm Order
        # --------------------------------------------

        order = locked_payment.order

        order.payment_status = "PAID"
        order.status = "PROCESSING"

        order.save(
            update_fields=[
                "payment_status",
                "status",
                "updated_at",
            ]
        )

        transaction.on_commit(
            lambda: send_payment_confirmation_email(
                locked_payment
            )
        )
        return True