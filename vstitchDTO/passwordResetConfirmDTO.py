import re

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OTP_PATTERN = re.compile(r"^\d{6}$")


class PasswordResetConfirmDTO(BaseModel):
    email: str = Field(..., min_length=5, max_length=250)
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=250)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address.")
        return value.lower()

    @field_validator("otp")
    @classmethod
    def validate_otp_format(cls, value):
        if not OTP_PATTERN.match(value):
            raise ValueError("Enter the 6-digit code.")
        return value

    @field_validator("new_password")
    @classmethod
    def validate_password_byte_length(cls, value):
        # Same bcrypt 72-byte check as signupRequestDTO.py/
        # adminResetPasswordRequestDTO.py's new_password - "same rule as
        # /signup" per the spec.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return value
