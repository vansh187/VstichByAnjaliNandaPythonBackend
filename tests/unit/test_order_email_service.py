from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from vstitchServices.orderEmailService import OrderEmailService

SAMPLE_ORDER = {
    "vstitch_order_id": 42,
    "payment_method": "cod",
    "total_amount": 2998.0,
    "shipping_recipient_name": "Anjali Nanda",
    "shipping_address_line1": "12 MG Road",
    "shipping_address_line2": None,
    "shipping_city": "Mumbai",
    "shipping_state": "MH",
    "shipping_postal_code": "400001",
    "shipping_country": "India",
    "shipping_phone_number": "+919876543210",
    "created_date": datetime(2026, 7, 10, 14, 22, 0),
    "email": "anjali@example.com",
    "items": [
        {
            "vstitch_order_item_id": 101,
            "vstitch_product_variant_id": 12,
            "vstitch_product_id": 7,
            "product_name": "Anarkali Kurti",
            "size": "M",
            "color": "Blue",
            "unit_price": 1499.0,
            "quantity": 2,
            "sku": "SKU-101",
        }
    ],
}


@pytest.fixture
def order_email_service():
    service = OrderEmailService()
    service.order_persistence = MagicMock()
    service.invoice_pdf_service = MagicMock()
    service.invoice_pdf_service.build_invoice_pdf.return_value = b"%PDF-fake"
    return service


@pytest.fixture(autouse=True)
def admin_email_env(monkeypatch):
    monkeypatch.setenv("VSTITCH_ADMIN_NOTIFICATION_EMAIL", "admin@example.com")


def test_sends_both_emails_on_success(order_email_service):
    order_email_service.order_persistence.get_order_for_confirmation_email.return_value = SAMPLE_ORDER

    with patch("vstitchServices.orderEmailService.ResendEmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        order_email_service.send_order_confirmation_emails(42)

    assert mock_client.send_email.call_count == 2
    customer_call, admin_call = mock_client.send_email.call_args_list
    assert customer_call.args[0] == "anjali@example.com"
    assert customer_call.kwargs["attachments"][0]["filename"] == "VStitch-Invoice-42.pdf"
    assert admin_call.args[0] == "admin@example.com"


def test_does_nothing_when_order_not_found(order_email_service):
    order_email_service.order_persistence.get_order_for_confirmation_email.return_value = None

    with patch("vstitchServices.orderEmailService.ResendEmailClient") as mock_client_cls:
        order_email_service.send_order_confirmation_emails(999)

    mock_client_cls.assert_not_called()


def test_admin_email_still_sent_when_pdf_generation_fails(order_email_service):
    order_email_service.order_persistence.get_order_for_confirmation_email.return_value = SAMPLE_ORDER
    order_email_service.invoice_pdf_service.build_invoice_pdf.side_effect = Exception("reportlab blew up")

    with patch("vstitchServices.orderEmailService.ResendEmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        order_email_service.send_order_confirmation_emails(42)

    assert mock_client.send_email.call_count == 2
    customer_call, _admin_call = mock_client.send_email.call_args_list
    assert customer_call.kwargs["attachments"] is None


def test_admin_email_still_sent_when_customer_email_fails(order_email_service):
    order_email_service.order_persistence.get_order_for_confirmation_email.return_value = SAMPLE_ORDER

    with patch("vstitchServices.orderEmailService.ResendEmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.send_email.side_effect = [Exception("resend down"), None]
        order_email_service.send_order_confirmation_emails(42)

    assert mock_client.send_email.call_count == 2


def test_admin_email_skipped_when_env_var_missing(order_email_service, monkeypatch):
    monkeypatch.delenv("VSTITCH_ADMIN_NOTIFICATION_EMAIL", raising=False)
    order_email_service.order_persistence.get_order_for_confirmation_email.return_value = SAMPLE_ORDER

    with patch("vstitchServices.orderEmailService.ResendEmailClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        order_email_service.send_order_confirmation_emails(42)

    # Only the customer email goes out - admin send is skipped entirely.
    assert mock_client.send_email.call_count == 1
    assert mock_client.send_email.call_args_list[0].args[0] == "anjali@example.com"


def test_never_raises_when_persistence_blows_up(order_email_service):
    order_email_service.order_persistence.get_order_for_confirmation_email.side_effect = Exception("db down")

    # Must not raise - this is called from inside a payment webhook / order
    # placement flow that must never fail because of an email problem.
    order_email_service.send_order_confirmation_emails(42)
