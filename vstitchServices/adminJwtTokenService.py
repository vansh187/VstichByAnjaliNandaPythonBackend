import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()


class AdminJwtTokenService:
    """Issues and decodes the JWT access tokens used to authenticate admin
    requests. Deliberately a separate service/secret from JwtTokenService
    (customer tokens), not an extension of it - admin and customer are
    different principal types backed by different tables
    (VStitch_AdminUsers vs VStitch_Users); keeping the token issuance and
    verification paths fully separate means a customer token can never be
    mistaken for (or accepted as) an admin one, or vice versa, regardless of
    what claims either payload happens to carry.
    """

    def __init__(self):
        self.jwt_secret = os.getenv("ADMIN_JWT_SECRET")
        self.jwt_algorithm = os.getenv("ADMIN_JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ADMIN_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        if not self.jwt_secret:
            raise ValueError("ADMIN_JWT_SECRET must be configured in the environment.")

    def generate_access_token(self, vstitch_admin_id, admin_username):
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        token_payload = {
            "sub": str(vstitch_admin_id),
            "admin_username": admin_username,
            "role": "admin",
            "exp": expires_at,
        }
        return jwt.encode(token_payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def decode_access_token(self, access_token):
        try:
            return jwt.decode(access_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except JWTError as token_error:
            raise ValueError("Invalid or expired admin access token.") from token_error
