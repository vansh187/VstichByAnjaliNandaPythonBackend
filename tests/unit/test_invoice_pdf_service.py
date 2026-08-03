from datetime import datetime

from vstitchServices.invoicePdfService import InvoicePdfService

SAMPLE_ORDER = {
    "vstitch_order_id": 42,
    "payment_method": "razorpay",
    "total_amount": 4497.0,
    "shipping_recipient_name": "Anjali Nanda",
    "shipping_address_line1": "12 MG Road",
    "shipping_address_line2": "Near Central Mall",
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
        },
        {
            "vstitch_order_item_id": 102,
            "vstitch_product_variant_id": None,
            "vstitch_product_id": None,
            "product_name": "Bridal Lehenga Choli",
            "size": None,
            "color": None,
            "unit_price": 1499.0,
            "quantity": 1,
            "sku": None,
        },
    ],
}


def test_builds_a_valid_pdf():
    pdf_bytes = InvoicePdfService().build_invoice_pdf(SAMPLE_ORDER)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_handles_missing_size_color_sku_without_raising():
    # Item 102 above has None size/color/sku (variant deleted after order
    # placement) - must not raise, not just "usually works".
    pdf_bytes = InvoicePdfService().build_invoice_pdf(SAMPLE_ORDER)
    assert pdf_bytes.startswith(b"%PDF")


def test_handles_missing_address_line2():
    order = {**SAMPLE_ORDER, "shipping_address_line2": None}
    pdf_bytes = InvoicePdfService().build_invoice_pdf(order)
    assert pdf_bytes.startswith(b"%PDF")
