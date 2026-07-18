-- VStitch_PaymentWebhookEvents: append-only audit log of every Razorpay webhook
-- delivery, keyed by Razorpay's own event id. Razorpay retries a webhook on any
-- non-2xx response or timeout, so this table is what makes webhook processing
-- idempotent - a replayed event is recognized by RazorpayEventId and skipped
-- instead of double-applying a status change or double-restocking inventory.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_PaymentWebhookEvents (
    VstitchPaymentWebhookEventId  BIGSERIAL     PRIMARY KEY,
    RazorpayEventId               VARCHAR(250)  NOT NULL,
    EventType                     VARCHAR(100)  NOT NULL,
    RazorpayOrderId               VARCHAR(250),
    RazorpayPaymentId             VARCHAR(250),
    Payload                       TEXT          NOT NULL,
    ProcessedSuccessfully         BOOLEAN       NOT NULL DEFAULT FALSE,
    created_date                  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_payment_webhook_events_event_id UNIQUE (RazorpayEventId)
);

CREATE INDEX IF NOT EXISTS idx_payment_webhook_events_razorpay_order_id ON VStitch_PaymentWebhookEvents (RazorpayOrderId);
