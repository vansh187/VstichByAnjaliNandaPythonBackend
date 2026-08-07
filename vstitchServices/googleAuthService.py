import os
import re
import secrets
from urllib.parse import urlencode

import psycopg2.errors
import requests
from dotenv import load_dotenv
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from vstitchDatabase.googleAuthPersistence import GoogleAuthPersistence
from vstitchDTO.loginResponseDTO import LoginResponseDTO
from vstitchServices.jwtTokenService import JwtTokenService

load_dotenv()

USERNAME_SANITIZE_PATTERN = re.compile(r"[^a-z0-9_]")
GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class GoogleAuthService:
    """Business logic for signing in (or signing up) a VStitch_Users account
    via a Google ID token. Verification happens entirely against Google's own
    published certs (via the google-auth library) - no secret round-trip to
    Google is needed, since only the CLIENT_ID (as the expected audience) is
    required to validate a token minted by Google Identity Services on the
    frontend.
    """

    def __init__(self):
        self.google_auth_persistence = GoogleAuthPersistence()
        self.jwt_token_service = JwtTokenService()
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_auth_request = google_requests.Request()
        if not self.google_client_id:
            raise ValueError("GOOGLE_CLIENT_ID must be configured in the environment.")
        # Only required for the server-driven authorization-code redirect
        # flow (build_authorization_url / authenticate_with_code) - checked
        # lazily in those methods rather than here, so a deployment that
        # only uses the legacy GSI id_token flow (authenticate_with_google)
        # doesn't fail to start without them.
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.google_oauth_redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

    def authenticate_with_google(self, google_login_request_dto):
        payload = self._verify_id_token(google_login_request_dto.id_token)
        return self._authenticate_from_payload(payload)

    def build_authorization_url(self, state):
        """Builds the Google OAuth 2.0 consent-screen URL for the
        authorization-code redirect flow. `state` is the caller-generated
        CSRF token, expected back unchanged on the callback."""
        if not self.google_oauth_redirect_uri:
            raise ValueError("GOOGLE_OAUTH_REDIRECT_URI must be configured in the environment.")
        query_params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": state,
        }
        return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(query_params)}"

    def authenticate_with_code(self, authorization_code):
        """Exchanges an authorization code for tokens server-side, verifies
        the returned id_token, and signs the user in - the callback-side
        half of the redirect flow started by build_authorization_url."""
        id_token_value = self._exchange_code_for_id_token(authorization_code)
        payload = self._verify_id_token(id_token_value)
        return self._authenticate_from_payload(payload)

    def _exchange_code_for_id_token(self, authorization_code):
        if not self.google_client_secret or not self.google_oauth_redirect_uri:
            raise ValueError("Google sign-in is not fully configured on the server.")
        try:
            token_response = requests.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": authorization_code,
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "redirect_uri": self.google_oauth_redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
        except requests.RequestException as request_error:
            raise ValueError("Could not reach Google to complete sign-in. Please try again.") from request_error

        if token_response.status_code != 200:
            raise ValueError("Google rejected the sign-in request. Please try again.")

        id_token_value = token_response.json().get("id_token")
        if not id_token_value:
            raise ValueError("Google did not return a valid credential. Please try again.")
        return id_token_value

    def _authenticate_from_payload(self, payload):
        google_id = payload.get("sub")
        email = payload.get("email")
        email_verified = payload.get("email_verified", False)
        if not google_id or not email or not email_verified:
            raise ValueError("This Google account has no verified email and cannot be used to sign in.")

        user_record = self.google_auth_persistence.get_user_by_google_id(google_id)
        if user_record is None:
            user_record = self._link_or_create_user(google_id, email, payload)

        access_token = self.jwt_token_service.generate_access_token(
            user_record["vstitch_user_id"], user_record["vstitch_user_name"]
        )
        return LoginResponseDTO(
            access_token=access_token,
            token_type="bearer",
            vstitch_user_id=user_record["vstitch_user_id"],
            vstitch_user_name=user_record["vstitch_user_name"],
        )

    def _verify_id_token(self, id_token_value):
        try:
            return google_id_token.verify_oauth2_token(
                id_token_value, self.google_auth_request, audience=self.google_client_id
            )
        except (GoogleAuthError, ValueError) as token_error:
            # ValueError: malformed token / wrong audience / expired - raised
            # directly by verify_oauth2_token, not wrapped in GoogleAuthError.
            raise ValueError("Invalid or expired Google credential.") from token_error

    def _link_or_create_user(self, google_id, email, payload):
        existing_local_account = self.google_auth_persistence.get_user_by_email(email)
        if existing_local_account is not None:
            return self.google_auth_persistence.link_google_id_to_user(
                existing_local_account["vstitch_user_id"], google_id, "google-oauth"
            )

        first_name = payload.get("given_name") or (payload.get("name", "").split(" ")[0] if payload.get("name") else "Google")
        last_name = payload.get("family_name") or "User"
        username = self._generate_unique_username(email, google_id)

        try:
            return self.google_auth_persistence.create_google_user(
                username, first_name, last_name, email, google_id, "google-oauth"
            )
        except psycopg2.errors.UniqueViolation:
            # A concurrent request for the same Google account (e.g. a
            # double-click) already created or linked this user - recover
            # idempotently instead of surfacing a 500 for a login retry.
            recovered = self.google_auth_persistence.get_user_by_google_id(
                google_id
            ) or self.google_auth_persistence.get_user_by_email(email)
            if recovered is None:
                raise ValueError("Could not complete Google sign-in. Please try again.")
            return recovered

    def _generate_unique_username(self, email, google_id):
        base = USERNAME_SANITIZE_PATTERN.sub("", email.split("@")[0].lower())[:40] or "user"
        if not self.google_auth_persistence.is_username_taken(base):
            return base
        for _ in range(5):
            candidate = f"{base}_{secrets.randbelow(10000):04d}"
            if not self.google_auth_persistence.is_username_taken(candidate):
                return candidate
        return f"google_{google_id[-16:]}"
