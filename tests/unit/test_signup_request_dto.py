import pytest
from pydantic import ValidationError

from vstitchDTO.signupRequestDTO import SignupRequestDTO

VALID_PAYLOAD = {
    "vstitch_user_name": "vansh_dev",
    "password": "Str0ngPass!",
    "first_name": "Vansh",
    "last_name": "Duggal",
    "email": "vansh@example.com",
    "phone_number": "+919876543210",
}


def test_accepts_a_valid_payload():
    dto = SignupRequestDTO(**VALID_PAYLOAD)
    assert dto.vstitch_user_name == "vansh_dev"
    assert dto.email == "vansh@example.com"


def test_lowercases_email():
    payload = {**VALID_PAYLOAD, "email": "Vansh@Example.COM"}
    dto = SignupRequestDTO(**payload)
    assert dto.email == "vansh@example.com"


def test_rejects_invalid_email():
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}
    with pytest.raises(ValidationError):
        SignupRequestDTO(**payload)


def test_rejects_invalid_phone_number():
    payload = {**VALID_PAYLOAD, "phone_number": "abc123"}
    with pytest.raises(ValidationError):
        SignupRequestDTO(**payload)


def test_rejects_short_password():
    payload = {**VALID_PAYLOAD, "password": "short"}
    with pytest.raises(ValidationError):
        SignupRequestDTO(**payload)


def test_rejects_password_over_72_bytes():
    payload = {**VALID_PAYLOAD, "password": "A" * 73}
    with pytest.raises(ValidationError):
        SignupRequestDTO(**payload)


def test_accepts_password_at_72_byte_boundary():
    payload = {**VALID_PAYLOAD, "password": "A" * 72}
    dto = SignupRequestDTO(**payload)
    assert len(dto.password) == 72
