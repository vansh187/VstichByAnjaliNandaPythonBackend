-- VStitch_PaymentTransactions: one or more gateway transactions per order, for
-- webhook reconciliation (a failed-then-retried payment gets a second row rather
-- than overwriting the first). Depends on VStitch_Orders.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_PaymentTransactions (
    VstitchPaymentTransactionId  BIGSERIAL     PRIMARY KEY,
    VstitchOrderId               BIGINT        NOT NULL REFERENCES VStitch_Orders(VstitchOrderId) ON DELETE CASCADE,
    GatewayTransactionId         VARCHAR(250)  NOT NULL,
    GatewayName                  VARCHAR(50)   NOT NULL,
    PaymentStatus                VARCHAR(20)   NOT NULL
                                     CHECK (PaymentStatus IN ('initiated', 'success', 'failed', 'refunded')),
    Amount                       NUMERIC(10,2) NOT NULL CHECK (Amount >= 0),
    created_by                   VARCHAR(250)  NOT NULL,
    created_date                 TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by                   VARCHAR(250),
    updated_date                 TIMESTAMP,

    CONSTRAINT uq_payment_transactions_gateway_id UNIQUE (GatewayTransactionId)
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_order_id ON VStitch_PaymentTransactions (VstitchOrderId);
