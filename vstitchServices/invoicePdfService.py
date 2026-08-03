import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BRAND_NAME = "VStitch by Anjali Nanda"
BRAND_COLOR = colors.HexColor("#7A2E3B")
LIGHT_ROW_COLOR = colors.HexColor("#F6EDEF")
BORDER_COLOR = colors.HexColor("#D9C6CB")

INVOICE_PAGE_MARGIN_MM = 18


class InvoicePdfService:
    """Builds the branded PDF order invoice attached to the customer
    order-confirmation email. Pure function of an order dict shaped like
    OrderPersistence.get_order_for_confirmation_email's return value - no DB
    access of its own, so it's trivially unit-testable against a plain dict.
    """

    def build_invoice_pdf(self, order):
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=INVOICE_PAGE_MARGIN_MM * mm,
            bottomMargin=INVOICE_PAGE_MARGIN_MM * mm,
            leftMargin=INVOICE_PAGE_MARGIN_MM * mm,
            rightMargin=INVOICE_PAGE_MARGIN_MM * mm,
            title=f"{BRAND_NAME} - Invoice #{order['vstitch_order_id']}",
        )

        styles = self._build_styles()
        elements = []
        elements.extend(self._build_header(order, styles))
        elements.append(Spacer(1, 8 * mm))
        elements.extend(self._build_billing_block(order, styles))
        elements.append(Spacer(1, 8 * mm))
        elements.append(self._build_items_table(order))
        elements.append(Spacer(1, 10 * mm))
        elements.append(self._build_footer(styles))

        document.build(elements)
        return buffer.getvalue()

    def _build_styles(self):
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="BrandTitle",
                parent=styles["Title"],
                textColor=BRAND_COLOR,
                fontSize=20,
                spaceAfter=2,
            )
        )
        styles.add(
            ParagraphStyle(
                name="InvoiceMeta",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#555555"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="SectionLabel",
                parent=styles["Normal"],
                fontSize=9,
                textColor=BRAND_COLOR,
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="FooterNote",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#777777"),
            )
        )
        return styles

    def _build_header(self, order, styles):
        created_date = order["created_date"]
        formatted_date = created_date.strftime("%d %b %Y") if created_date else "-"
        return [
            Paragraph(BRAND_NAME, styles["BrandTitle"]),
            Paragraph("TAX INVOICE / ORDER CONFIRMATION", styles["InvoiceMeta"]),
            Spacer(1, 4 * mm),
            Paragraph(f"Invoice / Order #: <b>{order['vstitch_order_id']}</b>", styles["InvoiceMeta"]),
            Paragraph(f"Order Date: {formatted_date}", styles["InvoiceMeta"]),
            Paragraph(f"Payment Method: {order['payment_method'].upper()}", styles["InvoiceMeta"]),
        ]

    def _build_billing_block(self, order, styles):
        address_lines = [order["shipping_address_line1"]]
        if order["shipping_address_line2"]:
            address_lines.append(order["shipping_address_line2"])
        address_lines.append(
            f"{order['shipping_city']}, {order['shipping_state']} {order['shipping_postal_code']}"
        )
        address_lines.append(order["shipping_country"])

        return [
            Paragraph("SHIP TO", styles["SectionLabel"]),
            Paragraph(order["shipping_recipient_name"], styles["Normal"]),
            *[Paragraph(line, styles["Normal"]) for line in address_lines],
            Paragraph(f"Phone: {order['shipping_phone_number']}", styles["Normal"]),
        ]

    def _build_items_table(self, order):
        header_row = ["Product", "Size", "Color", "Qty", "Unit Price", "Line Total"]
        table_rows = [header_row]
        for item in order["items"]:
            line_total = float(item["unit_price"]) * item["quantity"]
            table_rows.append(
                [
                    item["product_name"],
                    item["size"] or "-",
                    item["color"] or "-",
                    str(item["quantity"]),
                    f"Rs. {float(item['unit_price']):,.2f}",
                    f"Rs. {line_total:,.2f}",
                ]
            )
        table_rows.append(["", "", "", "", "Total", f"Rs. {float(order['total_amount']):,.2f}"])

        table = Table(table_rows, colWidths=[55 * mm, 18 * mm, 22 * mm, 12 * mm, 28 * mm, 28 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -2), 0.5, BORDER_COLOR),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_ROW_COLOR]),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("LINEABOVE", (0, -1), (-1, -1), 1, BRAND_COLOR),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    def _build_footer(self, styles):
        return Paragraph(
            "Thank you for shopping with VStitch by Anjali Nanda. For any questions about this order, "
            "reply to this email and our team will get back to you.",
            styles["FooterNote"],
        )
