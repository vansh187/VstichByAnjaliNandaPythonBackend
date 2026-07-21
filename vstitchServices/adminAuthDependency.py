from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from vstitchDatabase.adminUserPersistence import AdminUserPersistence
from vstitchServices.adminJwtTokenService import AdminJwtTokenService

bearer_scheme = HTTPBearer()
admin_jwt_token_service = AdminJwtTokenService()
admin_user_persistence = AdminUserPersistence()


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Decodes the bearer token issued at /admin/login into the calling
    admin's identity. Also checks the role claim explicitly (not just that
    the token decodes) - belt-and-suspenders against ADMIN_JWT_SECRET ever
    being accidentally set equal to JWT_SECRET in some environment, which
    would otherwise let a customer token satisfy this dependency.

    Also enforces revocation: fetches the admin's current
    TokenValidAfterUtc and rejects any token whose "iat" predates it - see
    AdminUserPersistence.revoke_all_sessions / POST /admin/logout-all. This
    is the one DB call in the request path that gives an otherwise-stateless
    JWT a real revocation mechanism; an explicit, accepted trade-off (see
    the security-hardening plan) rather than an oversight.
    """
    try:
        token_payload = admin_jwt_token_service.decode_access_token(credentials.credentials)
        if token_payload.get("role") != "admin":
            raise ValueError("Token does not carry an admin role.")
        vstitch_admin_id = int(token_payload["sub"])
        issued_at = int(token_payload["iat"])

        admin_record = admin_user_persistence.get_admin_by_id(vstitch_admin_id)
        if admin_record is None or not admin_record["is_active"]:
            raise ValueError("Admin account no longer exists or is inactive.")

        token_valid_after_utc = admin_record["token_valid_after_utc"]
        if token_valid_after_utc is not None:
            issued_at_utc = datetime.fromtimestamp(issued_at, tz=timezone.utc).replace(tzinfo=None)
            if issued_at_utc < token_valid_after_utc:
                raise ValueError("Token was issued before the admin's last logout-all - revoked.")

        return {
            "vstitch_admin_id": vstitch_admin_id,
            "admin_username": token_payload["admin_username"],
        }
    except (ValueError, KeyError, TypeError) as token_error:
        raise HTTPException(status_code=401, detail="Invalid or expired admin access token.") from token_error
