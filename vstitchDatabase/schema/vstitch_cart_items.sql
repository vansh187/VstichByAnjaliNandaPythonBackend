-- VStitch_CartItems: one row per (user, variant) in a customer's live cart.
-- No separate "cart" header table - a cart has no attributes of its own beyond its owner.
-- Depends on VStitch_Users and VStitch_ProductVariants.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_CartItems (
    VstitchCartItemId        BIGSERIAL     PRIMARY KEY,
    VstitchUserId            BIGINT        NOT NULL REFERENCES VStitch_Users(VstitchUserId) ON DELETE CASCADE,
    VstitchProductVariantId  BIGINT        NOT NULL REFERENCES VStitch_ProductVariants(VstitchProductVariantId) ON DELETE CASCADE,
    Quantity                 INTEGER       NOT NULL CHECK (Quantity > 0),
    created_by               VARCHAR(250)  NOT NULL,
    created_date             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by               VARCHAR(250),
    updated_date             TIMESTAMP,

    CONSTRAINT uq_cart_items_user_variant UNIQUE (VstitchUserId, VstitchProductVariantId)
);

CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON VStitch_CartItems (VstitchUserId);
CREATE INDEX IF NOT EXISTS idx_cart_items_variant_id ON VStitch_CartItems (VstitchProductVariantId);
