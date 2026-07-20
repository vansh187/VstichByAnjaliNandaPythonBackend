from fastapi import APIRouter, HTTPException

from vstitchDTO.adminLoginRequestDTO import AdminLoginRequestDTO
from vstitchDTO.adminLoginResponseDTO import AdminLoginResponseDTO
from vstitchServices.adminAuthService import AdminAuthService


class AdminAuthApi:
    """Exposes /admin/login. Deliberately its own router with no
    Depends(get_current_admin) - a caller can't present an admin bearer
    token they don't have yet, so this is the one admin endpoint that must
    stay open (rate limiting / lockout is a future hardening step, not
    something this codebase does anywhere yet for the customer /login
    either).
    """

    def __init__(self):
        self.admin_auth_service = AdminAuthService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/admin/login",
            self.login,
            methods=["POST"],
            response_model=AdminLoginResponseDTO,
        )

    def login(self, admin_login_request_dto: AdminLoginRequestDTO):
        try:
            return self.admin_auth_service.login(admin_login_request_dto)
        except ValueError as auth_error:
            raise HTTPException(status_code=401, detail=str(auth_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while logging in. Please try again later.",
            )


admin_auth_api = AdminAuthApi()
admin_auth_router = admin_auth_api.router
