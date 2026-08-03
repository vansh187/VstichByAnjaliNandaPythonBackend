-- VStitch_ReturnOrders: one row per customer-initiated return. A return is a
-- distinct Shiprocket order (pickup = customer address, delivery = our
-- warehouse) with its own Shiprocket order_id/shipment_id - tracked/cancelled
-- through the same APIs as a forward shipment. Depends on VStitch_Orders.
-- Engine: PostgreSQL.

-- RequestType distinguishes a plain customer return from a replace request
-- (size/defect issue on specific items) - both file the same kind of
-- Shiprocket return-pickup shipment, so both are tracked in this one table
-- rather than a parallel set. A replace row also has matching rows in
-- VStitch_ReturnOrderItems (see vstitch_return_order_items.sql); a plain
-- return has none (whole-order). Added by
-- migrations/0010_add_delivered_date_and_replace_requests.sql.
CREATE TABLE IF NOT EXISTS VStitch_ReturnOrders (
    VstitchReturnOrderId     BIGSERIAL     PRIMARY KEY,
    VstitchOrderId           BIGINT        NOT NULL REFERENCES VStitch_Orders(VstitchOrderId) ON DELETE RESTRICT,
    RequestType              VARCHAR(20)   NOT NULL DEFAULT 'return'
                                 CHECK (RequestType IN ('return', 'replace')),
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

-- DB-enforced invariant: at most one OPEN (not rejected/cancelled/completed)
-- return/replace request per order - closes the TOCTOU window in
-- ShipmentService._assert_no_open_return_request's own SELECT-then-decide
-- check. A second concurrent INSERT that would violate this fails with a
-- UniqueViolation, which OrderPersistence translates into a friendly
-- ValueError. Added by
-- migrations/0012_add_return_orders_open_request_unique_index.sql.
CREATE UNIQUE INDEX IF NOT EXISTS uq_return_orders_open_per_order
    ON VStitch_ReturnOrders (VstitchOrderId)
    WHERE Status NOT IN ('rejected', 'cancelled', 'completed');
