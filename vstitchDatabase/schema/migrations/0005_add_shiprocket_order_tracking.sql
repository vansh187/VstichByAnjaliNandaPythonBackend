-- Migration: adds the Shiprocket-side identifiers every fulfillment/tracking/
-- cancellation call needs. Our own VstitchOrderId is only usable for the
-- initial create-order call - every API after that (assign AWB, generate
-- pickup/label/manifest/invoice, track, cancel) is keyed by Shiprocket's own
-- order_id/shipment_id/awb_code, none of which were persisted anywhere.
--
-- VStitch_ReturnOrders is new - a return is a distinct Shiprocket order (pickup
-- = customer address, delivery = our warehouse) with its own order_id/
-- shipment_id, tracked/cancelled through the same APIs as a forward shipment
-- but representing a different real-world thing than the original order, so
-- it gets its own row rather than overloading VStitch_Orders.

ALTER TABLE VStitch_Orders
    ADD COLUMN IF NOT EXISTS ShiprocketOrderId     BIGINT,
    ADD COLUMN IF NOT EXISTS ShiprocketShipmentId  BIGINT,
    ADD COLUMN IF NOT EXISTS AwbCode                VARCHAR(100),
    ADD COLUMN IF NOT EXISTS CourierName            VARCHAR(250);

CREATE INDEX IF NOT EXISTS idx_orders_shiprocket_order_id ON VStitch_Orders (ShiprocketOrderId);

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
