import logging
import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from slowapi.util import get_remote_address

from vstitchDTO.googleLoginRequestDTO import GoogleLoginRequestDTO
from vstitchDTO.loginResponseDTO import LoginResponseDTO
from vstitchServices.googleAuthService import GoogleAuthService
from vstitchServices.rateLimiter import limiter

logger = logging.getLogger(__name__)

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_STATE_MAX_AGE_SECONDS = 300


class GoogleAuthApi:
    """Exposes the Google sign-in endpoints:
    - POST /auth/google - legacy GSI client-side id_token verification.
    - GET /auth/google/login + GET /auth/google/callback - server-driven
      OAuth 2.0 authorization-code redirect flow (works in FedCM-blocked
      contexts like Chrome Guest/Incognito, where the GSI widget cannot
      load an account chooser at all).
    """

    def __init__(self):
        self.google_auth_service = GoogleAuthService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/auth/google",
            self.login_with_google,
            methods=["POST"],
            response_model=LoginResponseDTO,
        )
        self.router.add_api_route(
            "/auth/google/login",
            self._build_google_login_route(),
            methods=["GET"],
        )
        self.router.add_api_route(
            "/auth/google/callback",
            self._build_google_callback_route(),
            methods=["GET"],
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

    def _build_google_login_route(self):
        # Plain closures, not bound instance methods - see the comment in
        # loginapi.py: slowapi's @limiter.limit inspects the decorated
        # function's own (unbound) parameter list to find "request" by
        # position, which desyncs from the real call args if `self` is
        # implicitly the first positional argument.
        google_auth_service = self.google_auth_service

        @limiter.limit("15/minute")
        def google_login(request: Request):
            try:
                state = secrets.token_urlsafe(32)
                authorization_url = google_auth_service.build_authorization_url(state)
            except ValueError as config_error:
                logger.error("Cannot start Google OAuth redirect flow: %s", config_error)
                raise HTTPException(status_code=500, detail="Google sign-in is not available right now.")

            redirect_response = RedirectResponse(url=authorization_url, status_code=302)
            redirect_response.set_cookie(
                key=OAUTH_STATE_COOKIE,
                value=state,
                max_age=OAUTH_STATE_MAX_AGE_SECONDS,
                httponly=True,
                secure=True,
                samesite="lax",
            )
            return redirect_response

        return google_login

    def _build_google_callback_route(self):
        google_auth_service = self.google_auth_service
        # Where the browser lands after a successful sign-in, with the
        # session handed off in the URL fragment (never sent to the server
        # on subsequent requests) for the frontend to read and store the
        # same way it already stores the token from POST /login and
        # POST /auth/google - kept as one consistent session mechanism
        # instead of introducing cookie-based sessions for only this path.
        post_login_redirect_url = os.getenv("GOOGLE_POST_LOGIN_REDIRECT_URL", "/")

        @limiter.limit("15/minute")
        def google_callback(request: Request, code: str = None, state: str = None, error: str = None):
            client_ip = get_remote_address(request)

            if error:
                logger.warning("Google OAuth callback returned an error (ip=%s): %s", client_ip, error)
                raise HTTPException(status_code=400, detail="Google sign-in was cancelled or failed.")

            cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
            state_is_valid = bool(code) and bool(state) and bool(cookie_state) and secrets.compare_digest(
                state, cookie_state
            )
            if not state_is_valid:
                logger.warning("Google OAuth callback failed CSRF state check (ip=%s)", client_ip)
                raise HTTPException(status_code=400, detail="Invalid state - possible CSRF")

            try:
                login_response = google_auth_service.authenticate_with_code(code)
            except ValueError as auth_error:
                logger.warning("Google OAuth code exchange failed (ip=%s): %s", client_ip, auth_error)
                raise HTTPException(status_code=401, detail=str(auth_error))
            except Exception:
                logger.exception("Unexpected error completing Google OAuth callback (ip=%s)", client_ip)
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while signing in with Google. Please try again later.",
                )

            # urlencode, not an f-string: vstitch_user_name is user-supplied
            # (no character-class validation at signup) and can contain
            # "&"/"#"/etc, which would otherwise corrupt the fragment for a
            # URLSearchParams-based parser on the frontend.
            fragment_params = urlencode(
                {
                    "token": login_response.access_token,
                    "token_type": login_response.token_type,
                    "vstitch_user_id": login_response.vstitch_user_id,
                    "vstitch_user_name": login_response.vstitch_user_name,
                }
            )
            redirect_response = RedirectResponse(url=f"{post_login_redirect_url}#{fragment_params}", status_code=302)
            redirect_response.delete_cookie(OAUTH_STATE_COOKIE)
            return redirect_response

        return google_callback


google_auth_api = GoogleAuthApi()
google_auth_router = google_auth_api.router
