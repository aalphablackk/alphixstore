import hashlib
import hmac
import json
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order
from orders.services import (
    release_order_stock,
    reserve_order_stock,
)

from .models import Payment
from .paystack import (
    PaystackError,
    verify_transaction,
)
from .services import (
    confirm_payment,
    fail_payment,
    initialize_payment,
)


# ============================================================
# INITIALIZE PAYMENT
# ============================================================

@login_required(login_url="/accounts/login/")
def initialize_payment_view(request, order_number):

    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user,
    )

    # --------------------------------------------------------
    # Already paid
    # --------------------------------------------------------

    if order.payment_status == "PAID":

        messages.info(
            request,
            "This order has already been paid for."
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    # --------------------------------------------------------
    # Check for an existing pending payment
    # --------------------------------------------------------

    pending_payment = (
        order.payments
        .filter(
            status=Payment.Status.PENDING
        )
        .order_by("-created_at")
        .first()
    )

    if pending_payment:

        if (
            pending_payment.expires_at
            and pending_payment.expires_at <= timezone.now()
        ):

            fail_payment(
                pending_payment
            )

        else:

            messages.info(
                request,
                "A payment is already in progress for this order."
            )

            return redirect(
                "order_detail",
                order_number=order.order_number,
            )

    # --------------------------------------------------------
    # Make sure stock is reserved
    # --------------------------------------------------------

    try:

        reserve_order_stock(order)

    except ValueError as exc:

        messages.error(
            request,
            str(exc)
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    # --------------------------------------------------------
    # Initialize Paystack payment
    # --------------------------------------------------------

    try:

        payment, response = initialize_payment(
            order=order,
            request=request,
        )

    except (
        PaystackError,
        ValueError,
    ) as exc:

        # Paystack initialization failed.
        # Release the stock that was just reserved.

        release_order_stock(order)

        messages.error(
            request,
            str(exc)
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    authorization_url = response.get(
        "authorization_url"
    )

    if not authorization_url:

        fail_payment(payment)

        messages.error(
            request,
            "Unable to initialize payment. Please try again."
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    return redirect(
        authorization_url
    )


# ============================================================
# PAYMENT CALLBACK
# ============================================================

@login_required(login_url="/accounts/login/")
def payment_callback(request):

    reference = (
        request.GET.get("reference")
        or request.GET.get("trxref")
    )

    # --------------------------------------------------------
    # Missing reference
    # --------------------------------------------------------

    if not reference:

        messages.error(
            request,
            "No payment reference was provided."
        )

        return redirect("my_orders")

    # --------------------------------------------------------
    # Find Payment
    # --------------------------------------------------------

    payment = get_object_or_404(
        Payment.objects.select_related(
            "order",
            "order__user",
        ),
        payment_reference=reference,
    )

    # --------------------------------------------------------
    # Security check
    # --------------------------------------------------------

    if payment.order.user != request.user:

        messages.error(
            request,
            "You are not authorized to access this payment."
        )

        return redirect("my_orders")

    # --------------------------------------------------------
    # Already successful
    # --------------------------------------------------------

    if payment.status == Payment.Status.SUCCESSFUL:

        messages.success(
            request,
            "Your payment has already been confirmed."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number,
        )

    # --------------------------------------------------------
    # Verify with Paystack
    # --------------------------------------------------------

    try:

        transaction_data = verify_transaction(
            reference
        )
        print("\n========== PAYSTACK DATA ==========")
        print(transaction_data)
        print("===================================\n")
    except PaystackError:

        messages.error(
            request,
            "We could not verify your payment right now. "
            "Please try again shortly."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number,
        )

    # --------------------------------------------------------
    # Verify reference
    # --------------------------------------------------------

    if (
        transaction_data.get("reference")
        != payment.payment_reference
    ):

        messages.error(
            request,
            "Payment verification failed."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number,
        )

    # --------------------------------------------------------
    # Verify currency
    # --------------------------------------------------------

    if (
        transaction_data.get("currency")
        != payment.currency
    ):

        fail_payment(payment)

        messages.error(
            request,
            "The payment currency could not be verified."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number,
        )

    # ---------------------------------
    # Verify amount
    # ---------------------------------

    requested_amount_kobo = transaction_data.get(
        "requested_amount"
    )

    if requested_amount_kobo is None:

        messages.error(
            request,
            "Payment amount could not be verified."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number
        )

    try:

        requested_amount_kobo = int(
            requested_amount_kobo
        )

    except (TypeError, ValueError):

        messages.error(
            request,
            "Invalid payment amount returned by Paystack."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number
        )


    expected_amount_kobo = int(
        payment.amount * Decimal("100")
    )


    if requested_amount_kobo != expected_amount_kobo:

        messages.error(
            request,
            "The payment amount could not be verified."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number
        )

        if paystack_amount_kobo != expected_amount_kobo:

            messages.error(
                request,
                "The payment amount could not be verified."
            )

            return redirect(
                "order_detail",
                order_number=payment.order.order_number
            )

    # --------------------------------------------------------
    # Verify Paystack status
    # --------------------------------------------------------

    if transaction_data.get("status") != "success":

        fail_payment(payment)

        messages.error(
            request,
            "Payment was not successful. "
            "You can try again."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number,
        )

    # --------------------------------------------------------
    # Confirm Payment
    # --------------------------------------------------------

    confirmed = confirm_payment(
        payment=payment,
        transaction_data=transaction_data,
    )

    if not confirmed:

        messages.info(
            request,
            "This payment has already been processed."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number,
        )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Do NOT clear the cart here.
    #
    # The cart is cleared when the order is created during
    # checkout.
    # --------------------------------------------------------

    messages.success(
        request,
        "Payment successful! Your order has been confirmed."
    )

    return redirect(
        "order_detail",
        order_number=payment.order.order_number,
    )


# ============================================================
# PAYSTACK WEBHOOK
# ============================================================

@csrf_exempt
def paystack_webhook(request):

    # --------------------------------------------------------
    # Only POST allowed
    # --------------------------------------------------------

    if request.method != "POST":

        return HttpResponse(
            status=405
        )

    # --------------------------------------------------------
    # Verify Paystack signature
    # --------------------------------------------------------

    signature = request.headers.get(
        "X-Paystack-Signature"
    )

    if not signature:

        return HttpResponse(
            status=401
        )

    expected_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        request.body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(
        signature,
        expected_signature,
    ):

        return HttpResponse(
            status=401
        )

    # --------------------------------------------------------
    # Parse webhook payload
    # --------------------------------------------------------

    try:

        payload = json.loads(
            request.body.decode("utf-8")
        )

    except (
        ValueError,
        UnicodeDecodeError,
    ):

        return HttpResponse(
            status=400
        )

    event = payload.get(
        "event"
    )

    # --------------------------------------------------------
    # Only successful charges are processed
    # --------------------------------------------------------

    if event != "charge.success":

        return HttpResponse(
            status=200
        )

    data = payload.get(
        "data",
        {}
    )

    reference = data.get(
        "reference"
    )

    if not reference:

        return HttpResponse(
            status=400
        )

    # --------------------------------------------------------
    # Find Payment
    # --------------------------------------------------------

    try:

        payment = (
            Payment.objects
            .select_related("order")
            .get(
                payment_reference=reference
            )
        )

    except Payment.DoesNotExist:

        # Unknown reference.
        #
        # Return 200 so Paystack does not repeatedly send
        # the same webhook forever.

        return HttpResponse(
            status=200
        )

    # --------------------------------------------------------
    # Already successful
    # --------------------------------------------------------

    if payment.status == Payment.Status.SUCCESSFUL:

        return HttpResponse(
            status=200
        )

    # --------------------------------------------------------
    # Independently verify with Paystack
    # --------------------------------------------------------

    try:

        transaction_data = verify_transaction(
            reference
        )
        print("\n========== PAYSTACK DATA ==========")
        print(transaction_data)
        print("===================================\n")
    except PaystackError:

        return HttpResponse(
            status=200
        )

    # --------------------------------------------------------
    # Verify reference
    # --------------------------------------------------------

    if (
        transaction_data.get("reference")
        != payment.payment_reference
    ):

        return HttpResponse(
            status=200
        )

    # --------------------------------------------------------
    # Verify currency
    # --------------------------------------------------------

    if (
        transaction_data.get("currency")
        != payment.currency
    ):

        return HttpResponse(
            status=200
        )

    # --------------------------------------------------------
    # Verify Paystack status
    # --------------------------------------------------------

    if (
        transaction_data.get("status")
        != "success"
    ):

        return HttpResponse(
            status=200
        )

    # --------------------------------------------------------
    # Verify amount
    # --------------------------------------------------------

    paystack_amount_kobo = transaction_data.get(
        "amount"
    )

    try:

        paystack_amount_kobo = int(
            paystack_amount_kobo
        )

    except (TypeError, ValueError):

        return HttpResponse(
            status=200
        )


    expected_amount_kobo = int(
        payment.amount * Decimal("100")
    )


    if paystack_amount_kobo != expected_amount_kobo:

        print(
            "PAYMENT AMOUNT DEBUG:",
            "Paystack:",
            paystack_amount_kobo,
            "Expected:",
            expected_amount_kobo,
            "Payment amount:",
            payment.amount,
        )

        messages.error(
            request,
            "The payment amount could not be verified."
        )

        return redirect(
            "order_detail",
            order_number=payment.order.order_number
        )

    # --------------------------------------------------------
    # Confirm payment
    # --------------------------------------------------------

    confirm_payment(
        payment=payment,
        transaction_data=transaction_data,
    )

    return HttpResponse(
        status=200
    )


# ============================================================
# RETRY PAYMENT
# ============================================================

@login_required(login_url="/accounts/login/")
def retry_payment(request, order_number):

    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user,
    )

    # --------------------------------------------------------
    # Already paid
    # --------------------------------------------------------

    if order.payment_status == "PAID":

        messages.info(
            request,
            "This order has already been paid for."
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    # --------------------------------------------------------
    # Find latest pending payment
    # --------------------------------------------------------

    pending_payment = (
        order.payments
        .filter(
            status=Payment.Status.PENDING
        )
        .order_by("-created_at")
        .first()
    )

    if pending_payment:

        # ----------------------------------------------------
        # Check expiration
        # ----------------------------------------------------

        if (
            pending_payment.expires_at
            and pending_payment.expires_at <= timezone.now()
        ):

            fail_payment(
                pending_payment
            )

        else:

            messages.info(
                request,
                "A payment is already in progress for this order."
            )

            return redirect(
                "order_detail",
                order_number=order.order_number,
            )

    # --------------------------------------------------------
    # Reserve stock again
    # --------------------------------------------------------

    try:

        reserve_order_stock(
            order
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc)
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    # --------------------------------------------------------
    # Create new payment attempt
    # --------------------------------------------------------

    try:

        payment, response = initialize_payment(
            order=order,
            request=request,
        )

    except (
        PaystackError,
        ValueError,
    ) as exc:

        # Paystack initialization failed.
        #
        # Release the stock we just reserved.

        release_order_stock(
            order
        )

        messages.error(
            request,
            str(exc)
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    # --------------------------------------------------------
    # Authorization URL
    # --------------------------------------------------------

    authorization_url = response.get(
        "authorization_url"
    )

    if not authorization_url:

        fail_payment(
            payment
        )

        messages.error(
            request,
            "Unable to initialize payment. Please try again."
        )

        return redirect(
            "order_detail",
            order_number=order.order_number,
        )

    return redirect(
        authorization_url
    )