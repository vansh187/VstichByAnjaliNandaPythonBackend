import pytest
from pydantic import ValidationError

from vstitchDTO.customizationRequestDTO import CreateCustomizationRequestDTO

VALID_PAYLOAD = {
    "customer_name": "Anjali Sharma",
    "customer_phone": "+91 98765 43210",
    "bust_in": 36,
    "waist_in": 30,
    "hips_in": 39,
    "shoulder_in": 14.5,
    "sleeve_length_in": 22,
    "dress_length_in": 42,
    "notes": "Slightly looser through the waist, please.",
}


def test_accepts_a_valid_payload():
    dto = CreateCustomizationRequestDTO(**VALID_PAYLOAD)
    assert dto.customer_name == "Anjali Sharma"
    assert dto.notes == "Slightly looser through the waist, please."


def test_notes_is_optional():
    payload = {**VALID_PAYLOAD}
    del payload["notes"]
    dto = CreateCustomizationRequestDTO(**payload)
    assert dto.notes is None


def test_rejects_whitespace_only_name():
    payload = {**VALID_PAYLOAD, "customer_name": "   "}
    with pytest.raises(ValidationError):
        CreateCustomizationRequestDTO(**payload)


def test_rejects_whitespace_only_phone():
    payload = {**VALID_PAYLOAD, "customer_phone": "       "}
    with pytest.raises(ValidationError):
        CreateCustomizationRequestDTO(**payload)


def test_rejects_measurement_out_of_range():
    payload = {**VALID_PAYLOAD, "bust_in": 0}
    with pytest.raises(ValidationError):
        CreateCustomizationRequestDTO(**payload)


def test_rejects_negative_measurement():
    payload = {**VALID_PAYLOAD, "waist_in": -5}
    with pytest.raises(ValidationError):
        CreateCustomizationRequestDTO(**payload)


def test_rounds_measurements_to_two_decimal_places():
    payload = {**VALID_PAYLOAD, "bust_in": 34.567}
    dto = CreateCustomizationRequestDTO(**payload)
    assert dto.bust_in == 34.57


def test_rounds_half_up():
    payload = {**VALID_PAYLOAD, "waist_in": 30.005}
    dto = CreateCustomizationRequestDTO(**payload)
    assert dto.waist_in == 30.01


def test_rejects_over_length_phone():
    payload = {**VALID_PAYLOAD, "customer_phone": "1" * 51}
    with pytest.raises(ValidationError):
        CreateCustomizationRequestDTO(**payload)
