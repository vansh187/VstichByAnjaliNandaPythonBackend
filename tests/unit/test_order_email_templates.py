from datetime import datetime

from vstitchServices.orderEmailTemplates import build_admin_notification_email, build_customer_confirmation_email

SAMPLE_ORDER = {
    "vstitch_order_id": 42,
    "payment_method": "cod",
    "total_amount": 2998.0,
    "shipping_recipient_name": "<script>alert(1)</script>",
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


def test_customer_email_escapes_html_in_user_supplied_fields():
    _subject, html_body = build_customer_confirmation_email(SAMPLE_ORDER)
    assert "<script>alert(1)</script>" not in html_body
    assert "&lt;script&gt;" in html_body


def test_customer_email_includes_order_id_and_total():
    subject, html_body = build_customer_confirmation_email(SAMPLE_ORDER)
    assert "42" in subject
    assert "#42" in html_body
    assert "2,998.00" in html_body


def test_customer_email_shows_cod_payment_note():
    _subject, html_body = build_customer_confirmation_email(SAMPLE_ORDER)
    assert "Cash on Delivery" in html_body


def test_customer_email_shows_paid_note_for_razorpay():
    order = {**SAMPLE_ORDER, "payment_method": "razorpay"}
    _subject, html_body = build_customer_confirmation_email(order)
    assert "Payment received" in html_body


def test_admin_email_includes_product_and_variant_ids():
    _subject, html_body = build_admin_notification_email(SAMPLE_ORDER)
    assert ">7<" in html_body  # vstitch_product_id
    assert ">12<" in html_body  # vstitch_product_variant_id
    assert "SKU-101" in html_body


def test_admin_email_handles_missing_variant_gracefully():
    order = {
        **SAMPLE_ORDER,
        "items": [
            {
                "vstitch_order_item_id": 101,
                "vstitch_product_variant_id": None,
                "vstitch_product_id": None,
                "product_name": "Anarkali Kurti",
                "size": None,
                "color": None,
                "unit_price": 1499.0,
                "quantity": 1,
                "sku": None,
            }
        ],
    }
    _subject, html_body = build_admin_notification_email(order)
    assert "N/A" in html_body


def test_admin_email_escapes_html_in_user_supplied_fields():
    _subject, html_body = build_admin_notification_email(SAMPLE_ORDER)
    assert "<script>alert(1)</script>" not in html_body
