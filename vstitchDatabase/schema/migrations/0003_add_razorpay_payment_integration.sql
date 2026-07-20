-- Migration: adds Razorpay online-payment support alongside the existing COD flow.
-- Run once, directly against Supabase (matches how the rest of the schema is
-- applied - see README "Database schema").
--
-- 1. VStitch_Orders gains 'razorpay' as a PaymentMethod and two new OrderStatus
--    values that only apply to the online-payment flow: 'payment_pending' (order
--    row + stock decrement exist, gateway order created, waiting on the customer
--    to actually pay) and 'payment_failed' (terminal - stock has been restored).
--    A razorpay order that succeeds transitions payment_pending -> placed and
--    rejoins the existing COD pipeline from there onward; COD orders are
--    unaffected and still start at 'placed' directly.
-- 2. VStitch_PaymentTransactions is redesigned - it was added in an earlier
--    migration but has zero rows and no code references it yet, so it's safe to
--    replace its columns outright rather than layer on top. One row per gateway
--    order attempt, keyed by RazorpayOrderId; RazorpayPaymentId/PaymentStatus
--    fill in once the webhook confirms an outcome. Linked to VStitch_Orders
--    (not directly to a product) because one Razorpay payment covers an order's
--    full multi-product basket - product-level detail already lives one hop away
--    via VStitch_OrderItems.
-- 3. VStitch_PaymentWebhookEvents is new - an append-only audit log of every
--    webhook Razorpay sends, keyed by its own event id. Razorpay retries
--    webhooks on any non-2xx/timeout response, so this table is what makes
--    webhook processing idempotent (a replayed event is recognized and skipped
--    instead of double-applying a status change or double-restocking).

ALTER TABLE VStitch_Orders
    DROP CONSTRAINT IF EXISTS vstitch_orders_paymentmethod_check;
ALTER TABLE VStitch_Orders
    ADD CONSTRAINT vstitch_orders_paymentmethod_check CHECK (PaymentMethod IN ('cod', 'razorpay'));

ALTER TABLE VStitch_Orders
    DROP CONSTRAINT IF EXISTS vstitch_orders_orderstatus_check;
ALTER TABLE VStitch_Orders
    ADD CONSTRAINT vstitch_orders_orderstatus_check CHECK (OrderStatus IN (
        'payment_pending', 'payment_failed',
        'placed', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered',
        'cancelled', 'delivery_failed'
    ));

ALTER TABLE VStitch_PaymentTransactions
    DROP CONSTRAINT IF EXISTS uq_payment_transactions_gateway_id;
ALTER TABLE VStitch_PaymentTransactions
    DROP COLUMN IF EXISTS GatewayTransactionId;
ALTER TABLE VStitch_PaymentTransactions
    DROP CONSTRAINT IF EXISTS vstitch_paymenttransactions_paymentstatus_check;

ALTER TABLE VStitch_PaymentTransactions
    ALTER COLUMN GatewayName SET DEFAULT 'razorpay',
    ADD COLUMN IF NOT EXISTS RazorpayOrderId    VARCHAR(250),
    ADD COLUMN IF NOT EXISTS RazorpayPaymentId   VARCHAR(250),
    ADD COLUMN IF NOT EXISTS RazorpaySignature   VARCHAR(500),
    ADD COLUMN IF NOT EXISTS Currency            VARCHAR(10) NOT NULL DEFAULT 'INR',
    ADD COLUMN IF NOT EXISTS FailureReason        VARCHAR(500);

ALTER TABLE VStitch_PaymentTransactions
    ALTER COLUMN RazorpayOrderId SET NOT NULL,
    ALTER COLUMN PaymentStatus SET DEFAULT 'created';

ALTER TABLE VStitch_PaymentTransactions
    ADD CONSTRAINT vstitch_paymenttransactions_paymentstatus_check
        CHECK (PaymentStatus IN ('created', 'authorized', 'captured', 'failed', 'refunded'));

ALTER TABLE VStitch_PaymentTransactions
    ADD CONSTRAINT uq_payment_transactions_razorpay_order_id UNIQUE (RazorpayOrderId);
ALTER TABLE VStitch_PaymentTransactions
    ADD CONSTRAINT uq_payment_transactions_razorpay_payment_id UNIQUE (RazorpayPaymentId);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_razorpay_order_id
    ON VStitch_PaymentTransactions (RazorpayOrderId);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status
    ON VStitch_PaymentTransactions (PaymentStatus);

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

CREATE INDEX IF NOT EXISTS idx_payment_webhook_events_razorpay_order_id
    ON VStitch_PaymentWebhookEvents (RazorpayOrderId);
