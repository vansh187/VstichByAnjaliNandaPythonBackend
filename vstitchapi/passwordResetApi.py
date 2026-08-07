from fastapi import APIRouter, HTTPException, Request

from vstitchDTO.passwordResetConfirmDTO import PasswordResetConfirmDTO
from vstitchDTO.passwordResetRequestDTO import PasswordResetRequestDTO
from vstitchDTO.passwordResetResponseDTO import PasswordResetResponseDTO
from vstitchServices.passwordResetService import (
    InvalidOrExpiredOtpError,
    PasswordResetRequestError,
    PasswordResetService,
    TooManyOtpAttemptsError,
)
from vstitchServices.rateLimiter import limiter


class PasswordResetApi:
    """Exposes POST /password-reset/request and POST /password-reset/confirm
    - the email-OTP "Forgot password?" flow, entirely inside the existing
    login/signup modal. No auth on either endpoint: /request must be
    reachable by a logged-out visitor by definition, and the OTP itself is
    the credential for /confirm.
    """

    def __init__(self):
        self.password_reset_service = PasswordResetService()
        self.router = APIRouter(prefix="/password-reset")
        self.router.add_api_route(
            "/request",
            self._build_request_route(),
            methods=["POST"],
            response_model=PasswordResetResponseDTO,
        )
        self.router.add_api_route(
            "/confirm",
            self._build_confirm_route(),
            methods=["POST"],
            response_model=PasswordResetResponseDTO,
        )

    def _build_request_route(self):
        # A plain closure, not a bound instance method - see LoginApi.
        # _build_login_route's comment (loginapi.py) for why @limiter.limit
        # requires this.
        password_reset_service = self.password_reset_service

        # Rate limited: 5 requests/minute per IP - same unauthenticated-write
        # abuse profile as /signup and /subscribe. A per-email cooldown is
        # additionally enforced inside PasswordResetService itself
        # (OTP_RESEND_COOLDOWN_SECONDS), since this IP limit alone wouldn't
        # stop one IP from spamming many different victim inboxes.
        @limiter.limit("5/minute")
        def request_password_reset(request_dto: PasswordResetRequestDTO, request: Request):
            try:
                password_reset_service.request_otp(request_dto)
            except PasswordResetRequestError as request_error:
                raise HTTPException(status_code=500, detail=str(request_error))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong. Please try again later.",
                )
            # Always the same response whether or not the email is
            # registered - see PasswordResetService.request_otp's docstring.
            # This is what prevents the endpoint being used to enumerate
            # accounts.
            return PasswordResetResponseDTO(status="sent")

        return request_password_reset

    def _build_confirm_route(self):
        password_reset_service = self.password_reset_service

        # Rate limited: 5 requests/minute per IP - the actual brute-force
        # defense for the 6-digit code is PasswordResetService's own
        # MAX_OTP_ATTEMPTS lockout (this IP limit alone would still allow
        # thousands of guesses/day from a single IP against many accounts).
        @limiter.limit("5/minute")
        def confirm_password_reset(request_dto: PasswordResetConfirmDTO, request: Request):
            try:
                password_reset_service.confirm_reset(request_dto)
            except TooManyOtpAttemptsError as too_many_attempts_error:
                raise HTTPException(status_code=429, detail=str(too_many_attempts_error))
            except InvalidOrExpiredOtpError as invalid_otp_error:
                raise HTTPException(status_code=400, detail=str(invalid_otp_error))
            except PasswordResetRequestError as reset_error:
                raise HTTPException(status_code=500, detail=str(reset_error))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong. Please try again later.",
                )
            return PasswordResetResponseDTO(status="success")

        return confirm_password_reset


password_reset_api = PasswordResetApi()
password_reset_router = password_reset_api.router
