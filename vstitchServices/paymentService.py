import hashlib
import json
import uuid

from vstitchDatabase.paymentPersistence import PaymentPersistence
from vstitchDTO.paymentResponseDTO import CreatePaymentOrderResponseDTO
from vstitchServices.orderService import OrderService
from vstitchServices.razorpayClient import razorpay_client, to_paise

# Only these events change order/transaction state today - a young checkout
# flow only needs to react to "did the money land or not". Every other
# subscribed event (disputes, settlements, downtime, invoices, refund.*, ...)
# is still recorded in VStitch_PaymentWebhookEvents for audit, just without a
# business-logic handler yet - safe to no-op since we never told Razorpay we'd
# act on them.
CAPTURE_EVENT_TYPES = {"payment.captured"}
FAILURE_EVENT_TYPES = {"payment.failed"}


class PaymentService:
    """Business logic for Razorpay checkout: creating a gateway order for the
    user to pay against, and applying the outcome once the webhook reports it.
    """

    def __init__(self):
        self.order_service = OrderService()
        self.payment_persistence = PaymentPersistence()

    def create_payment_order(self, create_order_request_dto, vstitch_user_id, created_by_ip_address):
        # Validate/price first (read-only) - nothing is written or charged yet,
        # so an invalid basket fails fast with a 409 before touching Razorpay
        # or decrementing any stock.
        order_items, total_amount = self.order_service.validate_and_price_items(create_order_request_dto.items)

        # Call the gateway before writing anything to our own database: if
        # Razorpay is unreachable or rejects the request, we simply return an
        # error with zero side effects, instead of having to unwind a stock
        # decrement / order row that was already committed.
        razorpay_order = razorpay_client.create_order(
            amount_in_paise=to_paise(total_amount),
            currency="INR",
            receipt=f"vstitch-{uuid.uuid4().hex}",
        )

        vstitch_order_id, order_status, payment_method, inserted_total_amount = (
            self.order_service.create_pending_gateway_order(
                order_items,
                total_amount,
                create_order_request_dto,
                vstitch_user_id,
                created_by_ip_address,
                razorpay_order["id"],
            )
        )

        return CreatePaymentOrderResponseDTO(
            vstitch_order_id=vstitch_order_id,
            razorpay_order_id=razorpay_order["id"],
            razorpay_key_id=razorpay_client.key_id,
            amount=razorpay_order["amount"],
            currency=razorpay_order["currency"],
        )

    def verify_webhook_signature(self, raw_body, signature):
        return razorpay_client.verify_webhook_signature(raw_body, signature)

    def handle_webhook_event(self, raw_body):
        """Processes one already-signature-verified webhook delivery. Every
        exit path is idempotent: a byte-for-byte replayed delivery (Razorpay
        retries on any non-2xx/timeout) is recognized via the event
        fingerprint and skipped rather than re-applied.
        """
        body = json.loads(raw_body)
        event_type = body.get("event", "")
        payload = body.get("payload", {})
        payment_entity = payload.get("payment", {}).get("entity", {})
        order_entity = payload.get("order", {}).get("entity", {})

        razorpay_payment_id = payment_entity.get("id")
        razorpay_order_id = payment_entity.get("order_id") or order_entity.get("id")

        # Razorpay's payload doesn't reliably carry a top-level unique event id
        # across all account configurations, but a retried delivery repeats the
        # exact same body byte-for-byte - hashing the raw body is therefore a
        # correct idempotency key regardless of whether "id" is present.
        event_fingerprint = body.get("id") or hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        is_new_event = self.payment_persistence.record_webhook_event(
            event_fingerprint, event_type, razorpay_order_id, razorpay_payment_id, body
        )
        if not is_new_event:
            return

        if event_type in CAPTURE_EVENT_TYPES and razorpay_order_id:
            self.payment_persistence.mark_payment_captured(
                razorpay_order_id, razorpay_payment_id, None, "razorpay-webhook"
            )
        elif event_type in FAILURE_EVENT_TYPES and razorpay_order_id:
            failure_reason = payment_entity.get("error_description") or "Payment failed."
            self.payment_persistence.mark_payment_failed(
                razorpay_order_id, razorpay_payment_id, failure_reason, "razorpay-webhook"
            )

        self.payment_persistence.mark_webhook_event_processed(event_fingerprint)
