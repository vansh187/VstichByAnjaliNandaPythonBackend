-- VStitch_OrderItems: one row per line item in an order. Snapshots the product
-- name/size/color/price at time of purchase rather than relying solely on a live
-- join to VStitch_ProductVariants, so a later price change or product rename never
-- rewrites historical order data. Depends on VStitch_Orders and VStitch_ProductVariants.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_OrderItems (
    VstitchOrderItemId       BIGSERIAL     PRIMARY KEY,
    VstitchOrderId           BIGINT        NOT NULL REFERENCES VStitch_Orders(VstitchOrderId) ON DELETE CASCADE,
    VstitchProductVariantId  BIGINT        REFERENCES VStitch_ProductVariants(VstitchProductVariantId) ON DELETE SET NULL,
    ProductNameSnapshot      VARCHAR(250)  NOT NULL,
    SizeSnapshot             VARCHAR(50),
    ColorSnapshot            VARCHAR(50),
    UnitPriceSnapshot        NUMERIC(10,2) NOT NULL CHECK (UnitPriceSnapshot >= 0),
    Quantity                 INTEGER       NOT NULL CHECK (Quantity > 0),
    created_by               VARCHAR(250)  NOT NULL,
    created_date             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by               VARCHAR(250),
    updated_date             TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON VStitch_OrderItems (VstitchOrderId);
CREATE INDEX IF NOT EXISTS idx_order_items_variant_id ON VStitch_OrderItems (VstitchProductVariantId);
