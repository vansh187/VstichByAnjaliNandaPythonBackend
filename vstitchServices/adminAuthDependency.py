from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vstitchServices.adminJwtTokenService import AdminJwtTokenService

bearer_scheme = HTTPBearer()
admin_jwt_token_service = AdminJwtTokenService()


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Decodes the bearer token issued at /admin/login into the calling
    admin's identity. Also checks the role claim explicitly (not just that
    the token decodes) - belt-and-suspenders against ADMIN_JWT_SECRET ever
    being accidentally set equal to JWT_SECRET in some environment, which
    would otherwise let a customer token satisfy this dependency.
    """
    try:
        token_payload = admin_jwt_token_service.decode_access_token(credentials.credentials)
        if token_payload.get("role") != "admin":
            raise ValueError("Token does not carry an admin role.")
        return {
            "vstitch_admin_id": int(token_payload["sub"]),
            "admin_username": token_payload["admin_username"],
        }
    except (ValueError, KeyError, TypeError) as token_error:
        raise HTTPException(status_code=401, detail="Invalid or expired admin access token.") from token_error
