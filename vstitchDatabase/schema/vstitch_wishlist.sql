-- VStitch_Wishlist: one entry per (user, product) - product-level, not variant-level.
-- Depends on VStitch_Users and VStitch_Products.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_Wishlist (
    VstitchWishlistId  BIGSERIAL     PRIMARY KEY,
    VstitchUserId      BIGINT        NOT NULL REFERENCES VStitch_Users(VstitchUserId) ON DELETE CASCADE,
    VstitchProductId   BIGINT        NOT NULL REFERENCES VStitch_Products(VstitchProductId) ON DELETE CASCADE,
    created_by         VARCHAR(250)  NOT NULL,
    created_date       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by         VARCHAR(250),
    updated_date       TIMESTAMP,

    CONSTRAINT uq_wishlist_user_product UNIQUE (VstitchUserId, VstitchProductId)
);

CREATE INDEX IF NOT EXISTS idx_wishlist_user_id ON VStitch_Wishlist (VstitchUserId);
