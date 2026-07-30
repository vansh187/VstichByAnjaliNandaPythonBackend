import re

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AdminResetPasswordRequestDTO(BaseModel):
    admin_username: str = Field(..., min_length=3, max_length=250)
    email: str = Field(..., min_length=5, max_length=250)
    new_password: str = Field(..., min_length=8, max_length=250)

    @field_validator("admin_username", "email", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        # mode="before" runs ahead of type coercion, so `value` isn't
        # guaranteed to be a str yet (could be None, a number, etc. from a
        # malformed request) - only strip actual strings and let Pydantic's
        # normal type/length validation reject anything else with its usual
        # 422, rather than this validator raising an AttributeError on
        # None.strip().
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, email_value):
        if not EMAIL_PATTERN.match(email_value):
            raise ValueError("Enter a valid email address.")
        return email_value

    @field_validator("new_password")
    @classmethod
    def validate_password_byte_length(cls, password_value):
        # bcrypt hard-truncates at 72 bytes: two passwords sharing the same
        # first 72 bytes would otherwise hash identically and both validate.
        if len(password_value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return password_value
