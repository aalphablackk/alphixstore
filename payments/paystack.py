import requests

from django.conf import settings


# ============================================================
# PAYSTACK CONFIGURATION
# ============================================================

PAYSTACK_BASE_URL = settings.PAYSTACK_BASE_URL


# ============================================================
# EXCEPTIONS
# ============================================================

class PaystackError(Exception):
    """
    Raised when communication with Paystack fails
    or Paystack returns an unsuccessful response.
    """

    pass


# ============================================================
# HEADERS
# ============================================================

def _get_headers():
    """
    Return the headers required for authenticated
    Paystack API requests.
    """

    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError(
            "Paystack secret key is not configured."
        )

    return {
        "Authorization": (
            f"Bearer {settings.PAYSTACK_SECRET_KEY}"
        ),
        "Content-Type": "application/json",
    }


# ============================================================
# INITIALIZE TRANSACTION
# ============================================================

def initialize_transaction(
    *,
    email,
    amount,
    reference,
    callback_url,
    metadata=None,
):
    """
    Initialize a Paystack transaction.

    Parameters:
        email:
            Customer email address.

        amount:
            Amount in Naira as a Decimal or numeric value.

        reference:
            Unique CineFlow payment reference.

        callback_url:
            Fully-qualified URL Paystack should redirect to
            after the customer completes the transaction.

        metadata:
            Optional metadata attached to the transaction.

    Returns:
        Dictionary containing:
            authorization_url
            access_code
            reference
            raw
    """

    amount_in_kobo = int(
        round(float(amount) * 100)
    )

    payload = {
        "email": email,
        "amount": str(amount_in_kobo),
        "currency": "NGN",
        "reference": reference,
        "callback_url": callback_url,
    }

    if metadata is not None:
        payload["metadata"] = metadata

    try:
        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            headers=_get_headers(),
            json=payload,
            timeout=30,
        )

    except requests.RequestException as exc:
        raise PaystackError(
            "Unable to connect to Paystack."
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise PaystackError(
            "Paystack returned an invalid response."
        ) from exc

    if (
        response.status_code != 200
        or not data.get("status")
    ):
        raise PaystackError(
            data.get(
                "message",
                "Paystack transaction initialization failed.",
            )
        )

    transaction_data = data.get("data")

    if not transaction_data:
        raise PaystackError(
            "Paystack returned no transaction data."
        )

    authorization_url = transaction_data.get(
        "authorization_url"
    )

    access_code = transaction_data.get(
        "access_code"
    )

    returned_reference = transaction_data.get(
        "reference"
    )

    if not authorization_url:
        raise PaystackError(
            "Paystack did not return an authorization URL."
        )

    if not returned_reference:
        raise PaystackError(
            "Paystack did not return a transaction reference."
        )

    return {
        "authorization_url": authorization_url,
        "access_code": access_code,
        "reference": returned_reference,
        "raw": data,
    }


# ============================================================
# VERIFY TRANSACTION
# ============================================================

def verify_transaction(reference):
    """
    Verify a Paystack transaction using its reference.

    Returns:
        Paystack transaction data.
    """

    if not reference:
        raise PaystackError(
            "A payment reference is required."
        )

    try:
        response = requests.get(
            (
                f"{PAYSTACK_BASE_URL}"
                f"/transaction/verify/{reference}"
            ),
            headers=_get_headers(),
            timeout=30,
        )

    except requests.RequestException as exc:
        raise PaystackError(
            "Unable to connect to Paystack."
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise PaystackError(
            "Paystack returned an invalid response."
        ) from exc

    if (
        response.status_code != 200
        or not data.get("status")
    ):
        raise PaystackError(
            data.get(
                "message",
                "Paystack transaction verification failed.",
            )
        )

    transaction_data = data.get("data")

    if not transaction_data:
        raise PaystackError(
            "Paystack returned no verification data."
        )

    return transaction_data


# ============================================================
# CREATE REFUND
# ============================================================

def create_refund(
    *,
    transaction,
    amount=None,
    customer_note=None,
    merchant_note=None,
):
    """
    Initiate a Paystack refund.

    Parameters:
        transaction:
            Paystack transaction reference or transaction ID.

        amount:
            Optional refund amount in Naira.

            If omitted, Paystack processes a full refund.

        customer_note:
            Optional note visible to the customer.

        merchant_note:
            Optional internal/merchant refund note.

    Returns:
        Paystack refund data.

    Important:
        A successful response means the refund request was
        accepted/queued by Paystack. It does NOT necessarily
        mean the customer's money has already been received.
    """

    if not transaction:
        raise PaystackError(
            "A Paystack transaction reference or ID is required."
        )

    payload = {
        "transaction": transaction,
    }

    # --------------------------------------------------------
    # Optional refund amount
    # --------------------------------------------------------

    if amount is not None:

        amount_in_kobo = int(
            round(float(amount) * 100)
        )

        if amount_in_kobo <= 0:
            raise PaystackError(
                "Refund amount must be greater than zero."
            )

        payload["amount"] = str(
            amount_in_kobo
        )

    # --------------------------------------------------------
    # Optional notes
    # --------------------------------------------------------

    if customer_note:
        payload["customer_note"] = customer_note

    if merchant_note:
        payload["merchant_note"] = merchant_note

    # --------------------------------------------------------
    # Send refund request
    # --------------------------------------------------------

    try:

        response = requests.post(
            f"{PAYSTACK_BASE_URL}/refund",
            headers=_get_headers(),
            json=payload,
            timeout=30,
        )

    except requests.RequestException as exc:

        raise PaystackError(
            "Unable to connect to Paystack while "
            "processing the refund."
        ) from exc

    # --------------------------------------------------------
    # Parse response
    # --------------------------------------------------------

    try:

        data = response.json()

    except ValueError as exc:

        raise PaystackError(
            "Paystack returned an invalid refund response."
        ) from exc

    # --------------------------------------------------------
    # Check Paystack response
    # --------------------------------------------------------

    if (
        response.status_code != 200
        or not data.get("status")
    ):

        raise PaystackError(
            data.get(
                "message",
                "Paystack refund request failed.",
            )
        )

    refund_data = data.get("data")

    if not refund_data:

        raise PaystackError(
            "Paystack returned no refund data."
        )

    # --------------------------------------------------------
    # Return useful refund information
    # --------------------------------------------------------

    return {
        "status": refund_data.get("status"),
        "amount": refund_data.get("amount"),
        "currency": refund_data.get("currency"),
        "refund_id": refund_data.get("id"),
        "transaction": refund_data.get("transaction"),
        "expected_at": refund_data.get("expected_at"),
        "customer_note": refund_data.get(
            "customer_note"
        ),
        "merchant_note": refund_data.get(
            "merchant_note"
        ),
        "raw": data,
    }


# ============================================================
# FETCH REFUND
# ============================================================

def fetch_refund(refund_id):
    """
    Fetch the current status/details of a Paystack refund.

    Parameters:
        refund_id:
            Paystack refund ID returned when the refund was created.

    Returns:
        Paystack refund data.
    """

    if not refund_id:
        raise PaystackError(
            "A Paystack refund ID is required."
        )

    try:
        response = requests.get(
            f"{PAYSTACK_BASE_URL}/refund/{refund_id}",
            headers=_get_headers(),
            timeout=30,
        )

    except requests.RequestException as exc:
        raise PaystackError(
            "Unable to connect to Paystack while "
            "fetching the refund."
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise PaystackError(
            "Paystack returned an invalid refund response."
        ) from exc

    if (
        response.status_code != 200
        or not data.get("status")
    ):
        raise PaystackError(
            data.get(
                "message",
                "Unable to fetch Paystack refund.",
            )
        )

    refund_data = data.get("data")

    if not refund_data:
        raise PaystackError(
            "Paystack returned no refund data."
        )

    return refund_data