import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()


class JwtTokenService:
    """Issues and decodes the JWT access tokens used to authenticate requests."""

    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM")
        self.access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        if not self.jwt_secret or not self.jwt_algorithm:
            raise ValueError("JWT_SECRET and JWT_ALGORITHM must be configured in the environment.")

    def generate_access_token(self, vstitch_user_id, vstitch_user_name):
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        token_payload = {
            "sub": str(vstitch_user_id),
            "vstitch_user_name": vstitch_user_name,
            "exp": expires_at,
        }
        return jwt.encode(token_payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def decode_access_token(self, access_token):
        try:
            return jwt.decode(access_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except JWTError as token_error:
            raise ValueError("Invalid or expired access token.") from token_error
