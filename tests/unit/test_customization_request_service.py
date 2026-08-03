from unittest.mock import MagicMock

import pytest

from vstitchDTO.customizationRequestDTO import CreateCustomizationRequestDTO
from vstitchServices.customizationRequestService import CUSTOMIZATION_REQUEST_SOURCE, CustomizationRequestService

VALID_PAYLOAD = {
    "customer_name": "Anjali Sharma",
    "customer_phone": "+91 98765 43210",
    "bust_in": 36,
    "waist_in": 30,
    "hips_in": 39,
    "shoulder_in": 14.5,
    "sleeve_length_in": 22,
    "dress_length_in": 42,
    "notes": None,
}


@pytest.fixture
def customization_request_service():
    service = CustomizationRequestService()
    service.customization_request_persistence = MagicMock()
    return service


def test_creates_request_for_a_logged_in_user(customization_request_service):
    customization_request_service.customization_request_persistence.variant_belongs_to_product.return_value = True
    customization_request_service.customization_request_persistence.create_customization_request.return_value = {
        "vstitch_customization_request_id": 101,
        "vstitch_product_id": 42,
        "vstitch_product_variant_id": 317,
        "status": "pending",
        "created_at": "2026-08-03T10:15:00Z",
    }

    result = customization_request_service.create_request(
        42, 317, CreateCustomizationRequestDTO(**VALID_PAYLOAD), 7
    )

    assert result["vstitch_customization_request_id"] == 101
    call_args = customization_request_service.customization_request_persistence.create_customization_request.call_args
    assert call_args.args[2] == 7  # vstitch_user_id passed through
    assert call_args.args[-1] == CUSTOMIZATION_REQUEST_SOURCE  # created_by is a fixed source label, not user-derived


def test_creates_request_anonymously_when_no_user(customization_request_service):
    customization_request_service.customization_request_persistence.variant_belongs_to_product.return_value = True
    customization_request_service.customization_request_persistence.create_customization_request.return_value = {
        "vstitch_customization_request_id": 102,
        "vstitch_product_id": 42,
        "vstitch_product_variant_id": 317,
        "status": "pending",
        "created_at": "2026-08-03T10:15:00Z",
    }

    customization_request_service.create_request(42, 317, CreateCustomizationRequestDTO(**VALID_PAYLOAD), None)

    call_args = customization_request_service.customization_request_persistence.create_customization_request.call_args
    assert call_args.args[2] is None  # vstitch_user_id is NULL for anonymous submissions


def test_rejects_variant_not_belonging_to_product(customization_request_service):
    customization_request_service.customization_request_persistence.variant_belongs_to_product.return_value = False

    with pytest.raises(ValueError, match="was not found"):
        customization_request_service.create_request(
            42, 999, CreateCustomizationRequestDTO(**VALID_PAYLOAD), None
        )

    customization_request_service.customization_request_persistence.create_customization_request.assert_not_called()


def test_lists_requests_for_user(customization_request_service):
    customization_request_service.customization_request_persistence.get_requests_for_user.return_value = [
        {"vstitch_customization_request_id": 101}
    ]

    result = customization_request_service.list_requests_for_user(7)

    assert result == [{"vstitch_customization_request_id": 101}]
    customization_request_service.customization_request_persistence.get_requests_for_user.assert_called_once_with(7)
