import os
from decimal import ROUND_HALF_UP, Decimal

import razorpay
from razorpay.errors import SignatureVerificationError

RAZORPAY_REQUEST_TIMEOUT_SECONDS = 5


def to_paise(amount):
    """Converts a rupee amount (Decimal/float/int, 2 decimal places) to the
    integer paise Razorpay's API requires. Goes through Decimal rather than
    float*100 to avoid binary-float rounding artifacts (e.g. 19.99 * 100 !=
    1999 in plain float arithmetic).
    """
    return int((Decimal(str(amount)) * 100).to_integral_value(rounding=ROUND_HALF_UP))


class RazorpayClient:
    """Thin wrapper around the official Razorpay SDK - the only place
    credentials are read from the environment and the only place the SDK is
    touched directly, so the rest of the app depends on this module's
    interface rather than the SDK's.
    """

    def __init__(self):
        key_id = os.getenv("RAZORPAY_API_KEY")
        key_secret = os.getenv("RAZORPAY_SECRET_KEY")
        webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
        if not key_id or not key_secret:
            raise ValueError("RAZORPAY_API_KEY / RAZORPAY_SECRET_KEY are not configured in the environment.")
        if not webhook_secret:
            raise ValueError("RAZORPAY_WEBHOOK_SECRET is not configured in the environment.")
        self.key_id = key_id
        self.webhook_secret = webhook_secret
        self.client = razorpay.Client(auth=(key_id, key_secret))

    def create_order(self, amount_in_paise, currency, receipt):
        """Creates a Razorpay order. Bounded by a short timeout so a
        slow/unreachable gateway fails fast instead of holding the caller's
        already-validated checkout open indefinitely. Raises on failure
        (razorpay.errors.* or a requests exception) - the caller translates
        that into an HTTP error response; nothing is written to our own
        database until this call has already succeeded.
        """
        return self.client.order.create(
            data={
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": receipt,
                "payment_capture": 1,  # auto-capture - no separate manual-capture step to orchestrate
            },
            timeout=RAZORPAY_REQUEST_TIMEOUT_SECONDS,
        )

    def verify_webhook_signature(self, raw_body, signature):
        """Returns True only if `signature` (the X-Razorpay-Signature header) is
        a valid HMAC-SHA256 of `raw_body` keyed by the webhook secret. Never
        raises - a missing/invalid signature is an expected occurrence (a
        malformed or spoofed request), not a bug, so it's reported as False
        rather than propagated as an exception.
        """
        if not signature:
            return False
        try:
            return self.client.utility.verify_webhook_signature(raw_body, signature, self.webhook_secret)
        except SignatureVerificationError:
            return False


razorpay_client = RazorpayClient()
