import pytest
from pydantic import ValidationError

from vstitchDTO.customizationInterestDTO import CreateCustomizationInterestDTO

VALID_PAYLOAD = {
    "name": "Anjali Sharma",
    "phone": "+91 98765 43210",
    "email": "Anjali@Example.com",
}


def test_accepts_a_valid_payload():
    dto = CreateCustomizationInterestDTO(**VALID_PAYLOAD)
    assert dto.name == "Anjali Sharma"
    assert dto.email == "anjali@example.com"  # lowercased, same as signup


def test_rejects_whitespace_only_name():
    payload = {**VALID_PAYLOAD, "name": "   "}
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(**payload)


def test_rejects_whitespace_only_phone():
    payload = {**VALID_PAYLOAD, "phone": "       "}
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(**payload)


def test_rejects_invalid_email():
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(**payload)


def test_rejects_short_phone():
    payload = {**VALID_PAYLOAD, "phone": "12345"}
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(**payload)


def test_rejects_over_length_name():
    payload = {**VALID_PAYLOAD, "name": "A" * 251}
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(**payload)


def test_rejects_control_characters_in_name():
    # Header-injection guard: `name` lands directly in the notification
    # email's Subject line - a smuggled newline must never reach that far.
    payload = {**VALID_PAYLOAD, "name": "Anjali\r\nBcc: attacker@example.com"}
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(**payload)


def test_rejects_control_characters_in_phone():
    # Body-injection guard: `phone` lands unescaped in the notification
    # email's plain-text body - a smuggled newline could forge fake extra
    # lines (e.g. a fake "Email: ..." line) in what the admin reads.
    payload = {**VALID_PAYLOAD, "phone": "+91987654\r\nEmail: attacker@example.com"}
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(**payload)


def test_rejects_missing_fields():
    with pytest.raises(ValidationError):
        CreateCustomizationInterestDTO(name="Anjali Sharma")
