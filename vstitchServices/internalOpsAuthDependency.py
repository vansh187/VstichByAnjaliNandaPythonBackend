import hmac
import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# Stopgap gate for internal fulfillment/ops endpoints (AWB assignment,
# pickup/label/manifest/invoice generation, NDR) - there is no admin/staff
# role anywhere in this codebase yet (VStitch_Users has no role column, and
# the JWT issued at login carries no scope claim), so these routes can't be
# gated the same way customer endpoints are. A single shared secret checked
# via a header is the minimum needed to keep them off the public internet
# unauthenticated; replace with real admin-role auth once one exists.
INTERNAL_OPS_API_KEY_HEADER_NAME = "X-Internal-Ops-Api-Key"
api_key_header = APIKeyHeader(name=INTERNAL_OPS_API_KEY_HEADER_NAME, auto_error=False)


def require_internal_ops_key(provided_key: str = Security(api_key_header)):
    expected_key = os.getenv("INTERNAL_OPS_API_KEY")
    if not expected_key:
        # Fails closed: an unconfigured key must never be treated as "no
        # restriction" - that would silently expose every ops endpoint the
        # moment someone forgets to set this in a new environment.
        raise HTTPException(status_code=503, detail="Internal ops endpoints are not configured in this environment.")
    # Constant-time compare - this is a bearer secret, not a public value; a
    # timing side-channel on `==` is exactly the kind of thing worth closing
    # even though the practical risk here is low.
    if not provided_key or not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid or missing internal ops API key.")
