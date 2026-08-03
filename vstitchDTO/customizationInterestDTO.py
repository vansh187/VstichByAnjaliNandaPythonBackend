import re

from pydantic import BaseModel, Field, field_validator

# Same pattern as signupRequestDTO.py's EMAIL_PATTERN/PHONE_NUMBER_PATTERN -
# kept as a separate copy rather than importing theirs, since this DTO has
# its own field names/bounds (a pre-purchase contact form, not an account
# signup) and no reason to couple the two.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Rejects ASCII control characters (0x00-0x1F, 0x7F). Applied to both name
# and phone below: `name` ends up directly in the notification email's
# Subject line ("Customization Required By {name}") - a newline/CR smuggled
# in there is the classic email-header-injection corner case (attempting to
# inject extra headers or split the subject). `phone` ends up unescaped in
# the plain-text email *body* (build_customization_interest_email) - a
# smuggled \r\n there can't touch headers, but still lets a submission
# forge extra fake "lines" (e.g. a fake "Email: attacker@..." line) inside
# the body the admin reads. Neither is merely trusted because Resend's
# JSON API happens to make it hard to exploit today.
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


class CreateCustomizationInterestDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=250)
    phone: str = Field(..., min_length=7, max_length=50)
    email: str = Field(..., min_length=5, max_length=250)

    @field_validator("name", "phone")
    @classmethod
    def reject_blank_text(cls, value):
        # min_length already rejects a too-short/empty string, but not one
        # made entirely of whitespace ("   ") - not useful to the studio
        # trying to identify or call back the lead.
        if not value.strip():
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("name", "phone")
    @classmethod
    def reject_control_characters(cls, value):
        if CONTROL_CHARACTER_PATTERN.search(value):
            raise ValueError("This field cannot contain control characters.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address.")
        return value.lower()
