import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from vstitchDTO.coordinatesDTO import CoordinatesDTO

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_NUMBER_PATTERN = re.compile(r"^\+?[0-9]{7,15}$")


class SignupLocationDTO(CoordinatesDTO):
    pass


class SignupRequestDTO(BaseModel):
    vstitch_user_name: str = Field(..., min_length=3, max_length=250)
    password: str = Field(..., min_length=8, max_length=250)
    first_name: str = Field(..., min_length=1, max_length=250)
    last_name: str = Field(..., min_length=1, max_length=250)
    email: str = Field(..., min_length=5, max_length=250)
    phone_number: str = Field(..., min_length=7, max_length=250)
    # Both optional, and deliberately not cross-validated against each
    # other (e.g. rejecting `location` present without
    # `location_permission_granted: true`) - the frontend contract never
    # sends that combination, but an older/replayed client sending only
    # one of the two must still be accepted and stored as-is rather than
    # 422ing, per the spec: "treat a request with neither present ... the
    # same as a denied prompt, not a validation error".
    location_permission_granted: Optional[bool] = None
    location: Optional[SignupLocationDTO] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, email_value):
        if not EMAIL_PATTERN.match(email_value):
            raise ValueError("Enter a valid email address.")
        return email_value.lower()

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, phone_number_value):
        if not PHONE_NUMBER_PATTERN.match(phone_number_value):
            raise ValueError("Enter a valid phone number (7-15 digits, optional leading +).")
        return phone_number_value

    @field_validator("password")
    @classmethod
    def validate_password_byte_length(cls, password_value):
        # bcrypt hard-truncates at 72 bytes: two passwords sharing the same
        # first 72 bytes would otherwise hash identically and both validate.
        if len(password_value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return password_value
