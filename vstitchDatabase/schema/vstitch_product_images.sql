-- VStitch_ProductImages: product photos, optionally tagged to a specific variant/color.
-- Depends on VStitch_Products and VStitch_ProductVariants. Stores URLs pointing at
-- Supabase Storage, not binary image data.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_ProductImages (
    VstitchProductImageId    BIGSERIAL     PRIMARY KEY,
    VstitchProductId         BIGINT        NOT NULL REFERENCES VStitch_Products(VstitchProductId) ON DELETE CASCADE,
    VstitchProductVariantId  BIGINT        REFERENCES VStitch_ProductVariants(VstitchProductVariantId) ON DELETE CASCADE,
    ImageUrl                 VARCHAR(500)  NOT NULL,
    IsPrimary                BOOLEAN       NOT NULL DEFAULT FALSE,
    DisplayOrder             INTEGER       NOT NULL DEFAULT 0,
    created_by               VARCHAR(250)  NOT NULL,
    created_date             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by               VARCHAR(250),
    updated_date             TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON VStitch_ProductImages (VstitchProductId);
CREATE INDEX IF NOT EXISTS idx_product_images_variant_id ON VStitch_ProductImages (VstitchProductVariantId);
