-- VStitch_ReturnOrders: one row per customer-initiated return. A return is a
-- distinct Shiprocket order (pickup = customer address, delivery = our
-- warehouse) with its own Shiprocket order_id/shipment_id - tracked/cancelled
-- through the same APIs as a forward shipment. Depends on VStitch_Orders.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_ReturnOrders (
    VstitchReturnOrderId     BIGSERIAL     PRIMARY KEY,
    VstitchOrderId           BIGINT        NOT NULL REFERENCES VStitch_Orders(VstitchOrderId) ON DELETE RESTRICT,
    ShiprocketReturnOrderId  BIGINT,
    ShiprocketShipmentId     BIGINT,
    Reason                   VARCHAR(500)  NOT NULL,
    Status                   VARCHAR(20)   NOT NULL DEFAULT 'requested'
                                 CHECK (Status IN ('requested', 'approved', 'rejected', 'picked_up', 'completed', 'cancelled')),
    created_by               VARCHAR(250)  NOT NULL,
    created_date             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by               VARCHAR(250),
    updated_date             TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_return_orders_order_id ON VStitch_ReturnOrders (VstitchOrderId);
