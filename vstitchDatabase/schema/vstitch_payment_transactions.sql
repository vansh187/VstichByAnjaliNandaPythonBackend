-- VStitch_PaymentTransactions: one row per Razorpay order-creation attempt for
-- an order (a failed-then-retried payment gets a second row rather than
-- overwriting the first). Keyed by RazorpayOrderId, filled in with
-- RazorpayPaymentId/PaymentStatus once the webhook confirms an outcome. Linked
-- to VStitch_Orders rather than to a product directly - one payment covers an
-- order's full multi-product basket; product-level detail lives one hop away
-- via VStitch_OrderItems. Depends on VStitch_Orders.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_PaymentTransactions (
    VstitchPaymentTransactionId  BIGSERIAL     PRIMARY KEY,
    VstitchOrderId               BIGINT        NOT NULL REFERENCES VStitch_Orders(VstitchOrderId) ON DELETE CASCADE,
    GatewayName                  VARCHAR(50)   NOT NULL DEFAULT 'razorpay',
    RazorpayOrderId              VARCHAR(250)  NOT NULL,
    RazorpayPaymentId            VARCHAR(250),
    RazorpaySignature            VARCHAR(500),
    PaymentStatus                VARCHAR(20)   NOT NULL DEFAULT 'created'
                                     CHECK (PaymentStatus IN ('created', 'authorized', 'captured', 'failed', 'refunded')),
    Amount                       NUMERIC(10,2) NOT NULL CHECK (Amount >= 0),
    Currency                     VARCHAR(10)   NOT NULL DEFAULT 'INR',
    FailureReason                VARCHAR(500),
    created_by                   VARCHAR(250)  NOT NULL,
    created_date                 TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by                   VARCHAR(250),
    updated_date                 TIMESTAMP,

    CONSTRAINT uq_payment_transactions_razorpay_order_id UNIQUE (RazorpayOrderId),
    CONSTRAINT uq_payment_transactions_razorpay_payment_id UNIQUE (RazorpayPaymentId)
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_order_id ON VStitch_PaymentTransactions (VstitchOrderId);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_razorpay_order_id ON VStitch_PaymentTransactions (RazorpayOrderId);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON VStitch_PaymentTransactions (PaymentStatus);
