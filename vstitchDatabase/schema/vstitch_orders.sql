-- VStitch_Orders: one row per placed order. Snapshots the shipping address directly
-- rather than only FK'ing VStitch_Addresses, so a later address edit/delete never
-- rewrites what an order actually shipped to. Depends on VStitch_Users.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_Orders (
    VstitchOrderId         BIGSERIAL     PRIMARY KEY,
    VstitchUserId          BIGINT        NOT NULL REFERENCES VStitch_Users(VstitchUserId) ON DELETE RESTRICT,
    -- COD-specific pipeline - no 'paid' state, since cash is only collected at
    -- the DELIVERED step rather than upfront. See vstitchServices/orderStatus.py
    -- for the full transition map (placed -> confirmed -> processing -> shipped
    -- -> out_for_delivery -> delivered, with cancelled/delivery_failed exits).
    -- payment_pending/payment_failed are Razorpay-only: an online order starts
    -- at payment_pending and only reaches placed (rejoining the same pipeline)
    -- once the payment.captured webhook confirms the charge succeeded.
    OrderStatus            VARCHAR(20)   NOT NULL DEFAULT 'placed'
                               CHECK (OrderStatus IN ('payment_pending', 'payment_failed', 'placed', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled', 'delivery_failed')),
    PaymentMethod           VARCHAR(20)   NOT NULL DEFAULT 'cod' CHECK (PaymentMethod IN ('cod', 'razorpay')),
    TotalAmount            NUMERIC(10,2) NOT NULL CHECK (TotalAmount >= 0),
    ShippingRecipientName  VARCHAR(250)  NOT NULL,
    ShippingAddressLine1   VARCHAR(250)  NOT NULL,
    ShippingAddressLine2   VARCHAR(250),
    ShippingCity           VARCHAR(250)  NOT NULL,
    ShippingState          VARCHAR(250)  NOT NULL,
    ShippingPostalCode     VARCHAR(20)   NOT NULL,
    ShippingCountry        VARCHAR(250)  NOT NULL,
    ShippingPhoneNumber    VARCHAR(250)  NOT NULL,
    created_by             VARCHAR(250)  NOT NULL,
    created_date           TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by             VARCHAR(250),
    updated_date           TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON VStitch_Orders (VstitchUserId);
CREATE INDEX IF NOT EXISTS idx_orders_status ON VStitch_Orders (OrderStatus);
CREATE INDEX IF NOT EXISTS idx_orders_created_date ON VStitch_Orders (created_date);
