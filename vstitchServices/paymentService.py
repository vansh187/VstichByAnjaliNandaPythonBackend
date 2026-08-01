import hashlib
import json
import logging
import uuid

from vstitchDatabase.paymentPersistence import PaymentPersistence
from vstitchDTO.paymentResponseDTO import CreatePaymentOrderResponseDTO
from vstitchServices.orderService import OrderService
from vstitchServices.razorpayClient import razorpay_client, to_paise
from vstitchServices.shipmentService import ShipmentService

logger = logging.getLogger(__name__)

# Only these events change order/transaction state today - a young checkout
# flow only needs to react to "did the money land or not", plus (as of the
# return/replace refund flow) "did a refund we initiated actually land".
# Every other subscribed event (disputes, settlements, downtime, invoices,
# ...) is still recorded in VStitch_PaymentWebhookEvents for audit, just
# without a business-logic handler yet - safe to no-op since we never told
# Razorpay we'd act on them.
CAPTURE_EVENT_TYPES = {"payment.captured"}
FAILURE_EVENT_TYPES = {"payment.failed"}
REFUND_PROCESSED_EVENT_TYPES = {"refund.processed"}
REFUND_FAILED_EVENT_TYPES = {"refund.failed"}


class PaymentService:
    """Business logic for Razorpay checkout: creating a gateway order for the
    user to pay against, and applying the outcome once the webhook reports it.
    """

    def __init__(self):
        self.order_service = OrderService()
        self.payment_persistence = PaymentPersistence()
        # Constructed lazily per capture event, not here - a Shiprocket
        # config problem (e.g. SHIPROCKET_PICKUP_LOCATION unset) must never
        # stop PaymentService itself from being usable for checkout/webhook
        # signature verification, which have nothing to do with shipping.

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
            vstitch_order_id = self.payment_persistence.mark_payment_captured(
                razorpay_order_id, razorpay_payment_id, None, "razorpay-webhook"
            )
            # None means this delivery didn't actually transition anything (a
            # Razorpay retry of an already-applied capture, or an order in an
            # unexpected state) - nothing new was placed, so there's nothing
            # to ship.
            if vstitch_order_id is not None:
                self._create_shipment(vstitch_order_id)
        elif event_type in FAILURE_EVENT_TYPES and razorpay_order_id:
            failure_reason = payment_entity.get("error_description") or "Payment failed."
            self.payment_persistence.mark_payment_failed(
                razorpay_order_id, razorpay_payment_id, failure_reason, "razorpay-webhook"
            )
        elif event_type in REFUND_PROCESSED_EVENT_TYPES or event_type in REFUND_FAILED_EVENT_TYPES:
            # Confirms/reconciles a refund PaymentService.refund_order_payment
            # already initiated (return/replace reaching 'completed') -
            # .get() throughout, never direct-indexed, since a malformed or
            # differently-shaped refund payload must be logged and ignored
            # here, not raised (this method has no ValueError contract the
            # way the service layer elsewhere does; any raise here would
            # surface as a 500 to Razorpay and trigger an endless retry of a
            # webhook delivery that will never resolve differently).
            refund_entity = payload.get("refund", {}).get("entity", {})
            razorpay_refund_payment_id = refund_entity.get("payment_id")
            if razorpay_refund_payment_id:
                try:
                    if event_type in REFUND_PROCESSED_EVENT_TYPES:
                        refunded_amount_paise = refund_entity.get("amount") or 0
                        self.payment_persistence.mark_payment_refunded(
                            razorpay_refund_payment_id,
                            refunded_amount_paise / 100,
                            "razorpay-webhook",
                        )
                    else:
                        failure_reason = refund_entity.get("error_description") or "Refund failed."
                        self.payment_persistence.mark_payment_refund_failed(
                            razorpay_refund_payment_id, failure_reason, "razorpay-webhook"
                        )
                except Exception:
                    logger.exception(
                        "Failed to reconcile refund webhook event '%s' for payment %s.",
                        event_type,
                        razorpay_refund_payment_id,
                    )

        self.payment_persistence.mark_webhook_event_processed(event_fingerprint)

    def refund_order_payment(self, vstitch_order_id, reason, updated_by="system:return-completed"):
        """Issues a Razorpay refund for an order's captured payment -
        called when a return/replace request reaches 'completed'
        (AdminReturnService). Refunds the full originally-captured amount,
        always read server-side from VStitch_PaymentTransactions, never
        client-supplied. Raises ValueError if there's nothing to refund
        (COD order, not yet captured, or already refunded/in flight); lets
        any Razorpay/DB error propagate, since the caller here
        (AdminReturnService._try_trigger_refund) is the one responsible for
        catching broadly so a refund failure never fails the status update
        that triggered it.

        The captured -> refund_pending transition is claimed atomically
        BEFORE calling Razorpay, not after - update_return_status_admin has
        no old-status guard, so two admin requests completing the same
        return in quick succession can both reach this method; claiming
        first means only one of them ever actually calls Razorpay, and the
        second is rejected here with nothing charged twice.
        """
        transaction = self.payment_persistence.find_captured_transaction_by_order_id(vstitch_order_id)
        if transaction is None:
            raise ValueError(f"Order {vstitch_order_id} has no captured payment to refund.")

        razorpay_payment_id = transaction["razorpay_payment_id"]
        claimed_order_id = self.payment_persistence.mark_payment_refund_pending(razorpay_payment_id, updated_by)
        if claimed_order_id is None:
            raise ValueError(
                f"Order {vstitch_order_id}'s payment is no longer 'captured' - a refund may already be in "
                f"progress or completed (possibly from a concurrent request)."
            )

        amount_in_paise = to_paise(transaction["amount"])
        try:
            razorpay_refund = razorpay_client.refund_payment(
                razorpay_payment_id,
                amount_in_paise,
                notes={"reason": reason, "vstitch_order_id": str(vstitch_order_id)},
            )
        except Exception as gateway_error:
            # Reverts the claim (refund_pending -> captured) so this is
            # retryable - the customer was never actually charged/refunded
            # by this failed attempt, so there's nothing to reconcile beyond
            # freeing the transaction back up for a future retry.
            failure_reason = f"Refund request failed: {gateway_error}"[:500]
            self.payment_persistence.mark_payment_refund_failed(razorpay_payment_id, failure_reason, updated_by)
            raise ValueError(f"Refund request to Razorpay failed for order {vstitch_order_id}: {gateway_error}") from gateway_error

        self.payment_persistence.set_razorpay_refund_id(razorpay_payment_id, razorpay_refund.get("id"))
        return razorpay_refund

    def _create_shipment(self, vstitch_order_id):
        """Creates the Shiprocket shipment for a just-captured order. Never
        raises: this runs inside webhook processing, where an uncaught
        exception here would turn a successful, already-committed payment
        capture into a non-2xx response - causing Razorpay to retry a
        delivery that has nothing left to apply, without making the shipment
        any more likely to succeed the second time. The order/payment state
        is correct either way, so a shipment that fails to create is logged
        (with the full exception) rather than raised - logger.exception is
        the only record of it until this has its own retry-tracking table,
        so losing that record would make the failure untraceable.
        """
        try:
            ShipmentService().create_shipment_for_order(vstitch_order_id)
        except Exception:
            # Deliberately broad, not just ValueError: this is a cleanup-only
            # call at a hard webhook boundary, so even an unexpected bug here
            # (not just an expected Shiprocket/config failure) must not be
            # allowed to look like the webhook itself failed.
            logger.exception(
                "Shiprocket shipment creation failed for VStitch order %s - payment/order state is "
                "unaffected, but this order will need its shipment created manually.",
                vstitch_order_id,
            )
