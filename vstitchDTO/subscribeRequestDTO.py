import re

from pydantic import BaseModel, Field, field_validator

# Same pattern as customizationInterestDTO.py's EMAIL_PATTERN - kept as a
# separate copy rather than importing theirs, since this DTO has no reason
# to couple to an unrelated form.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SubscribeRequestDTO(BaseModel):
    email: str = Field(..., min_length=5, max_length=250)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address.")
        return value.lower()
