from fastapi import APIRouter, HTTPException

from vstitchDTO.loginRequestDTO import LoginRequestDTO
from vstitchDTO.loginResponseDTO import LoginResponseDTO
from vstitchServices.loginService import LoginService


class LoginApi:
    """Exposes the /login endpoint and translates service errors into HTTP responses."""

    def __init__(self):
        self.login_service = LoginService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/login",
            self.login,
            methods=["POST"],
            response_model=LoginResponseDTO,
        )

    def login(self, login_request_dto: LoginRequestDTO):
        try:
            return self.login_service.authenticate_user(login_request_dto)
        except ValueError as auth_error:
            raise HTTPException(status_code=401, detail=str(auth_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while logging in. Please try again later.",
            )


login_api = LoginApi()
login_router = login_api.router
