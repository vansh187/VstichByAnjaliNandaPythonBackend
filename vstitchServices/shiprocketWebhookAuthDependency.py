import hmac
import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# Shiprocket's webhook auth is a static shared secret it echoes back on the
# `x-api-key` header of every delivery (configured in Shiprocket's dashboard
# under Settings -> API -> Webhooks) - not an HMAC signature over the body
# like Razorpay's, so a plain header comparison is the correct check here.
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def require_shiprocket_webhook_key(provided_key: str = Security(api_key_header)):
    expected_key = os.getenv("SHIPROCKET_WEBHOOK_API_KEY")
    if not expected_key:
        # Fails closed: an unconfigured secret must never be treated as "no
        # restriction" - that would let anyone POST fake tracking events
        # that move real orders through the status pipeline.
        raise HTTPException(status_code=503, detail="Shiprocket webhook is not configured in this environment.")
    if not provided_key or not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid or missing webhook API key.")
