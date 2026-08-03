from unittest.mock import MagicMock, patch

import pytest

from vstitchDTO.customizationInterestDTO import CreateCustomizationInterestDTO
from vstitchServices.customizationInterestService import CustomizationInterestEmailError, CustomizationInterestService

VALID_PAYLOAD = {
    "name": "Anjali Sharma",
    "phone": "+91 98765 43210",
    "email": "anjali@example.com",
}


@pytest.fixture
def customization_interest_service():
    service = CustomizationInterestService()
    service.customization_interest_persistence = MagicMock()
    return service


@pytest.fixture(autouse=True)
def admin_email_env(monkeypatch):
    monkeypatch.setenv("VSTITCH_ADMIN_NOTIFICATION_EMAIL", "admin@example.com")


def test_saves_lead_and_sends_email_on_success(customization_interest_service):
    with patch("vstitchServices.customizationInterestService.ResendEmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        customization_interest_service.submit_interest(CreateCustomizationInterestDTO(**VALID_PAYLOAD))

    customization_interest_service.customization_interest_persistence.save_lead.assert_called_once_with(
        "Anjali Sharma", "+91 98765 43210", "anjali@example.com", "vstitch-ai-widget"
    )
    mock_client.send_email.assert_called_once()
    call_kwargs = mock_client.send_email.call_args.kwargs
    assert call_kwargs["headers"]["Importance"] == "high"
    assert "Anjali Sharma" in call_kwargs["text_body"]


def test_email_still_sent_when_lead_save_fails(customization_interest_service):
    customization_interest_service.customization_interest_persistence.save_lead.side_effect = Exception("db down")

    with patch("vstitchServices.customizationInterestService.ResendEmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # Must not raise - a lead-persistence failure is not this
        # endpoint's contract failure mode.
        customization_interest_service.submit_interest(CreateCustomizationInterestDTO(**VALID_PAYLOAD))

    mock_client.send_email.assert_called_once()


def test_raises_customization_interest_email_error_when_send_fails(customization_interest_service):
    with patch("vstitchServices.customizationInterestService.ResendEmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.send_email.side_effect = Exception("resend down")

        with pytest.raises(CustomizationInterestEmailError):
            customization_interest_service.submit_interest(CreateCustomizationInterestDTO(**VALID_PAYLOAD))

    # The lead is still saved even though the email ultimately failed -
    # valuable for manual follow-up regardless of the notification outcome.
    customization_interest_service.customization_interest_persistence.save_lead.assert_called_once()


def test_raises_customization_interest_email_error_when_resend_not_configured(customization_interest_service):
    with patch(
        "vstitchServices.customizationInterestService.ResendEmailClient", side_effect=ValueError("not configured")
    ):
        with pytest.raises(CustomizationInterestEmailError):
            customization_interest_service.submit_interest(CreateCustomizationInterestDTO(**VALID_PAYLOAD))


def test_raises_customization_interest_email_error_when_admin_email_env_missing(
    customization_interest_service, monkeypatch
):
    monkeypatch.delenv("VSTITCH_ADMIN_NOTIFICATION_EMAIL", raising=False)

    with patch("vstitchServices.customizationInterestService.ResendEmailClient") as mock_client_cls:
        with pytest.raises(CustomizationInterestEmailError):
            customization_interest_service.submit_interest(CreateCustomizationInterestDTO(**VALID_PAYLOAD))

    mock_client_cls.assert_not_called()
