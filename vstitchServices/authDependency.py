from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vstitchServices.jwtTokenService import JwtTokenService

bearer_scheme = HTTPBearer()
jwt_token_service = JwtTokenService()


def _resolve_user_from_token(access_token):
    """Shared decode/claims-extraction core for get_current_user and
    get_current_user_optional - the two functions differ only in how they
    react to a *missing* credential, never in how a *present* one is
    decoded, so that part lives in exactly one place.
    """
    try:
        token_payload = jwt_token_service.decode_access_token(access_token)
        return {
            "vstitch_user_id": int(token_payload["sub"]),
            "vstitch_user_name": token_payload["vstitch_user_name"],
        }
    except (ValueError, KeyError, TypeError) as token_error:
        # ValueError: signature/expiry rejected by decode_access_token.
        # KeyError/TypeError: a well-signed but unexpected payload shape (e.g. a
        # token from a future/older token schema) - still an auth failure, not a
        # server bug, so it must not fall through as an unhandled 500.
        raise HTTPException(status_code=401, detail="Invalid or expired access token.") from token_error


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Decodes the bearer token issued at login into the calling user's identity."""
    return _resolve_user_from_token(credentials.credentials)


def get_current_user_optional(request: Request):
    """Same decode as get_current_user, but for endpoints reachable while
    logged out (e.g. the customization-request form, browsable without an
    account): no Authorization header at all resolves to None rather than
    raising.

    Reads the raw header directly rather than depending on
    HTTPBearer(auto_error=False): that class returns None not only when the
    header is absent but also when it's present with the wrong scheme (e.g.
    "Basic ...") or otherwise malformed - which would silently downgrade a
    real, broken auth attempt to "anonymous" instead of surfacing it. Here,
    only a fully absent header is anonymous; anything else present is held
    to the same "valid or 401" standard as get_current_user.
    """
    authorization_header = request.headers.get("Authorization")
    if authorization_header is None:
        return None

    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")

    return _resolve_user_from_token(token)
