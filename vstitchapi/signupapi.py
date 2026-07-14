from fastapi import APIRouter, HTTPException, Request

from vstitchDTO.signupRequestDTO import SignupRequestDTO
from vstitchDTO.signupResponseDTO import SignupResponseDTO
from vstitchServices.signUpService import SignUpService


class SignupApi:
    """Exposes the /signup endpoint and translates service errors into HTTP responses."""

    def __init__(self):
        self.signup_service = SignUpService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/signup",
            self.signup,
            methods=["POST"],
            response_model=SignupResponseDTO,
        )

    def signup(self, signup_request_dto: SignupRequestDTO, request: Request):
        client_ip_address = request.client.host if request.client else "unknown"
        try:
            return self.signup_service.register_user(signup_request_dto, client_ip_address)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while creating the account. Please try again later.",
            )


signup_api = SignupApi()
signup_router = signup_api.router
