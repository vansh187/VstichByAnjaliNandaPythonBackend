from fastapi import APIRouter, HTTPException, Request

from vstitchDTO.loginRequestDTO import LoginRequestDTO
from vstitchDTO.loginResponseDTO import LoginResponseDTO
from vstitchServices.loginService import LoginService
from vstitchServices.rateLimiter import limiter


class LoginApi:
    """Exposes the /login endpoint and translates service errors into HTTP responses."""

    def __init__(self):
        self.login_service = LoginService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/login",
            self._build_login_route(),
            methods=["POST"],
            response_model=LoginResponseDTO,
        )

    def _build_login_route(self):
        # A plain closure, not a bound instance method: slowapi's @limiter.limit
        # inspects the decorated function's own parameter list to find
        # "request" by position, then indexes into the raw call args by that
        # position at request time. A bound method's descriptor protocol
        # sneaks `self` into that positional args tuple, which desyncs it
        # from the "request" position slowapi computed from the *unbound*
        # signature (which includes `self`) - crashing with
        # IndexError: tuple index out of range on every real request, even
        # though the route works fine outside of the decorator. A closure
        # over the service instance has no `self` parameter at all, so the
        # position slowapi computes matches the actual call every time.
        login_service = self.login_service

        # Rate limited (brute-force protection): 5 attempts/minute per
        # client IP, regardless of which username is being tried against.
        @limiter.limit("5/minute")
        def login(login_request_dto: LoginRequestDTO, request: Request):
            try:
                return login_service.authenticate_user(login_request_dto)
            except ValueError as auth_error:
                raise HTTPException(status_code=401, detail=str(auth_error))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while logging in. Please try again later.",
                )

        return login


login_api = LoginApi()
login_router = login_api.router
