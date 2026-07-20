from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vstitchServices.jwtTokenService import JwtTokenService

bearer_scheme = HTTPBearer()
jwt_token_service = JwtTokenService()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Decodes the bearer token issued at login into the calling user's identity."""
    try:
        token_payload = jwt_token_service.decode_access_token(credentials.credentials)
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
