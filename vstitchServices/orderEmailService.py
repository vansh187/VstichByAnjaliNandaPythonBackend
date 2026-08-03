import base64
import logging
import os

from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchServices.invoicePdfService import InvoicePdfService
from vstitchServices.orderEmailTemplates import build_admin_notification_email, build_customer_confirmation_email
from vstitchServices.resendEmailClient import ResendEmailClient

logger = logging.getLogger(__name__)


class OrderEmailService:
    """Sends the order-confirmation emails (customer, with a PDF invoice
    attached) and the internal "prepare for delivery" notification (admin
    fulfillment inbox) once an order is placed (COD) or its payment is
    captured (Razorpay). Every step is independently best-effort: a failure
    fetching the order, building the PDF, or sending either email is caught
    and logged at that exact step - never allowed to propagate into the
    order/payment flow that triggered it, and never allowed to silently
    take down a step that didn't actually fail (e.g. a broken PDF must not
    stop the customer email from sending without an attachment, and a
    failed customer send must not stop the admin notification from going
    out).
    """

    def __init__(self):
        self.order_persistence = OrderPersistence()
        self.invoice_pdf_service = InvoicePdfService()

    def send_order_confirmation_emails(self, vstitch_order_id):
        order = self._fetch_order(vstitch_order_id)
        if order is None:
            return

        pdf_bytes = self._build_invoice_pdf(order)
        self._send_customer_email(order, pdf_bytes)
        self._send_admin_email(order)

    def _fetch_order(self, vstitch_order_id):
        try:
            order = self.order_persistence.get_order_for_confirmation_email(vstitch_order_id)
        except Exception:
            logger.exception(
                "Failed to load order %s while preparing confirmation emails - no emails sent for this order.",
                vstitch_order_id,
            )
            return None
        if order is None:
            logger.warning(
                "Order %s not found while preparing confirmation emails - no emails sent for this order.",
                vstitch_order_id,
            )
        return order

    def _build_invoice_pdf(self, order):
        try:
            return self.invoice_pdf_service.build_invoice_pdf(order)
        except Exception:
            logger.exception(
                "PDF invoice generation failed for order %s - customer confirmation email will still be "
                "sent, without the invoice attached.",
                order["vstitch_order_id"],
            )
            return None

    def _send_customer_email(self, order, pdf_bytes):
        try:
            resend_client = ResendEmailClient()
        except ValueError:
            logger.exception(
                "Resend is not configured - customer confirmation email skipped for order %s.",
                order["vstitch_order_id"],
            )
            return

        attachments = None
        if pdf_bytes is not None:
            attachments = [
                {
                    "filename": f"VStitch-Invoice-{order['vstitch_order_id']}.pdf",
                    "content": base64.b64encode(pdf_bytes).decode("ascii"),
                }
            ]

        try:
            subject, html_body = build_customer_confirmation_email(order)
            resend_client.send_email(order["email"], subject, html_body, attachments=attachments)
        except Exception:
            logger.exception(
                "Failed to send customer confirmation email for order %s - order is unaffected.",
                order["vstitch_order_id"],
            )

    def _send_admin_email(self, order):
        # VSTITCH_RESEND_EMAIL, not VSTITCH_SHIPMENT_EMAIL: the latter is the
        # Shiprocket account login (see shiprocketClient.py) - an unrelated
        # credential that happens to share a value with this address today,
        # not the admin notification inbox. VSTITCH_RESEND_EMAIL is both the
        # Resend "from" sender and the studio's own inbox, per how it's
        # configured for this account.
        admin_email = os.getenv("VSTITCH_RESEND_EMAIL")
        if not admin_email:
            logger.warning(
                "VSTITCH_RESEND_EMAIL is not configured - admin order-notification email skipped for "
                "order %s.",
                order["vstitch_order_id"],
            )
            return

        try:
            resend_client = ResendEmailClient()
        except ValueError:
            logger.exception(
                "Resend is not configured - admin order-notification email skipped for order %s.",
                order["vstitch_order_id"],
            )
            return

        try:
            subject, html_body = build_admin_notification_email(order)
            resend_client.send_email(admin_email, subject, html_body)
        except Exception:
            logger.exception(
                "Failed to send admin order-notification email for order %s - order is unaffected.",
                order["vstitch_order_id"],
            )
