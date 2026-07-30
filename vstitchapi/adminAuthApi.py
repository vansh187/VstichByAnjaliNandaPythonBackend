from fastapi import APIRouter, Depends, HTTPException, Request

from vstitchDTO.adminLoginRequestDTO import AdminLoginRequestDTO
from vstitchDTO.adminLoginResponseDTO import AdminLoginResponseDTO
from vstitchDTO.adminResetPasswordRequestDTO import AdminResetPasswordRequestDTO
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.adminAuthService import AdminAuthService
from vstitchServices.rateLimiter import limiter


class AdminAuthApi:
    """Exposes /admin/login, /admin/reset-password, and /admin/logout-all.
    Login and reset-password are deliberately on their own router with no
    Depends(get_current_admin) - a caller can't present an admin bearer
    token they don't have yet (that's the whole point of a password reset),
    so these are the two admin endpoints that must stay open (rate-limited
    below instead of unprotected).
    """

    def __init__(self):
        self.admin_auth_service = AdminAuthService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/admin/login",
            self._build_login_route(),
            methods=["POST"],
            response_model=AdminLoginResponseDTO,
        )
        self.router.add_api_route(
            "/admin/reset-password",
            self._build_reset_password_route(),
            methods=["POST"],
            status_code=204,
        )
        self.router.add_api_route(
            "/admin/logout-all",
            self.logout_all,
            methods=["POST"],
            status_code=204,
            dependencies=[Depends(get_current_admin)],
        )

    def _build_login_route(self):
        # A plain closure, not a bound instance method - see LoginApi.
        # _build_login_route's comment in loginapi.py for why
        # @limiter.limit requires this.
        admin_auth_service = self.admin_auth_service

        # Rate limited (brute-force protection): 5 attempts/minute per
        # client IP.
        @limiter.limit("5/minute")
        def login(admin_login_request_dto: AdminLoginRequestDTO, request: Request):
            try:
                return admin_auth_service.login(admin_login_request_dto)
            except ValueError as auth_error:
                raise HTTPException(status_code=401, detail=str(auth_error))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while logging in. Please try again later.",
                )

        return login

    def _build_reset_password_route(self):
        admin_auth_service = self.admin_auth_service

        # Same 5/minute rate limit as login - this endpoint is an
        # unauthenticated username+email guessing surface otherwise, exactly
        # like login is an unauthenticated password guessing surface.
        @limiter.limit("5/minute")
        def reset_password(admin_reset_password_request_dto: AdminResetPasswordRequestDTO, request: Request):
            try:
                admin_auth_service.reset_password(admin_reset_password_request_dto)
            except ValueError as reset_error:
                raise HTTPException(status_code=404, detail=str(reset_error))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while resetting the password. Please try again later.",
                )

        return reset_password

    def logout_all(self, current_admin: dict = Depends(get_current_admin)):
        """Self-service 'log out everywhere' - revokes every access token
        issued to the calling admin before this moment (see
        AdminAuthService.revoke_all_sessions). Only revokes the caller's own
        sessions - no cross-admin revocation, since there's no role
        hierarchy yet to gate that safely.
        """
        try:
            self.admin_auth_service.revoke_all_sessions(
                current_admin["vstitch_admin_id"], f"admin:{current_admin['admin_username']}"
            )
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while logging out. Please try again later.",
            )


admin_auth_api = AdminAuthApi()
admin_auth_router = admin_auth_api.router
