from fastapi import APIRouter, HTTPException

from vstitchDTO.googleLoginRequestDTO import GoogleLoginRequestDTO
from vstitchDTO.loginResponseDTO import LoginResponseDTO
from vstitchServices.googleAuthService import GoogleAuthService


class GoogleAuthApi:
    """Exposes /auth/google and translates service errors into HTTP responses."""

    def __init__(self):
        self.google_auth_service = GoogleAuthService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/auth/google",
            self.login_with_google,
            methods=["POST"],
            response_model=LoginResponseDTO,
        )

    def login_with_google(self, google_login_request_dto: GoogleLoginRequestDTO):
        try:
            return self.google_auth_service.authenticate_with_google(google_login_request_dto)
        except ValueError as auth_error:
            raise HTTPException(status_code=401, detail=str(auth_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while signing in with Google. Please try again later.",
            )


google_auth_api = GoogleAuthApi()
google_auth_router = google_auth_api.router
