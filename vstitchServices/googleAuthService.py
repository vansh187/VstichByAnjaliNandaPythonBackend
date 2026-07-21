import os
import re
import secrets

import psycopg2.errors
from dotenv import load_dotenv
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from vstitchDatabase.googleAuthPersistence import GoogleAuthPersistence
from vstitchDTO.loginResponseDTO import LoginResponseDTO
from vstitchServices.jwtTokenService import JwtTokenService

load_dotenv()

USERNAME_SANITIZE_PATTERN = re.compile(r"[^a-z0-9_]")


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

    def authenticate_with_google(self, google_login_request_dto):
        payload = self._verify_id_token(google_login_request_dto.id_token)

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
