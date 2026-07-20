import json

from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class PaymentPersistence:
    """Database logic backing Razorpay webhook processing against
    VStitch_PaymentTransactions / VStitch_PaymentWebhookEvents / VStitch_Orders.
    """

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("payment_queries.yaml")

    def record_webhook_event(self, event_fingerprint, event_type, razorpay_order_id, razorpay_payment_id, payload):
        """Inserts the raw webhook delivery for audit + idempotency. Returns True
        if this is the first time this exact event has been seen (caller should
        process it), False if it's a Razorpay retry of an event already
        recorded (caller should skip processing and just acknowledge).
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_webhook_event"),
                    (
                        event_fingerprint,
                        event_type,
                        razorpay_order_id,
                        razorpay_payment_id,
                        json.dumps(payload),
                        False,
                    ),
                )
                inserted_row = cursor.fetchone()
            connection.commit()
            return inserted_row is not None

    def mark_webhook_event_processed(self, event_fingerprint):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("mark_webhook_event_processed"),
                    (event_fingerprint,),
                )
            connection.commit()

    def find_transaction_by_razorpay_order_id(self, razorpay_order_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("find_transaction_by_razorpay_order_id"),
                    (razorpay_order_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            column_names = ("vstitch_payment_transaction_id", "vstitch_order_id", "payment_status", "amount", "currency")
            return dict(zip(column_names, row))

    def mark_payment_captured(self, razorpay_order_id, razorpay_payment_id, razorpay_signature, updated_by):
        """Moves a transaction created/authorized -> captured and its order
        payment_pending -> placed, atomically. Guarded by old-status checks
        (see payment_queries.yaml) so a retried/duplicate webhook is a safe
        no-op rather than a double-apply. Returns the affected VstitchOrderId,
        or None if nothing matched (already processed, or an order in an
        unexpected state - caller treats either as "nothing to do").
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("update_transaction_status"),
                    {
                        "new_status": "captured",
                        "razorpay_payment_id": razorpay_payment_id,
                        "razorpay_signature": razorpay_signature,
                        "failure_reason": None,
                        "updated_by": updated_by,
                        "razorpay_order_id": razorpay_order_id,
                        "old_statuses": ["created", "authorized"],
                    },
                )
                transaction_row = cursor.fetchone()
                if transaction_row is None:
                    connection.commit()
                    return None
                vstitch_order_id = transaction_row[1]

                cursor.execute(
                    self.query_loader.get_query("update_order_status"),
                    {
                        "new_status": "placed",
                        "updated_by": updated_by,
                        "vstitch_order_id": vstitch_order_id,
                        "old_status": "payment_pending",
                    },
                )
                order_row = cursor.fetchone()
            connection.commit()
            return vstitch_order_id if order_row is not None else None

    def mark_payment_failed(self, razorpay_order_id, razorpay_payment_id, failure_reason, updated_by):
        """Moves a transaction created/authorized -> failed, its order
        payment_pending -> payment_failed, and restocks the variants that were
        held for it - all atomically, all guarded by old-status checks so a
        retried webhook can never restock the same order twice.
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("update_transaction_status"),
                    {
                        "new_status": "failed",
                        "razorpay_payment_id": razorpay_payment_id,
                        "razorpay_signature": None,
                        "failure_reason": failure_reason,
                        "updated_by": updated_by,
                        "razorpay_order_id": razorpay_order_id,
                        "old_statuses": ["created", "authorized"],
                    },
                )
                transaction_row = cursor.fetchone()
                if transaction_row is None:
                    connection.commit()
                    return None
                vstitch_order_id = transaction_row[1]

                cursor.execute(
                    self.query_loader.get_query("update_order_status"),
                    {
                        "new_status": "payment_failed",
                        "updated_by": updated_by,
                        "vstitch_order_id": vstitch_order_id,
                        "old_status": "payment_pending",
                    },
                )
                order_row = cursor.fetchone()
                if order_row is not None:
                    cursor.execute(
                        self.query_loader.get_query("restock_variants_for_order"),
                        (vstitch_order_id,),
                    )
            connection.commit()
            return vstitch_order_id if order_row is not None else None
