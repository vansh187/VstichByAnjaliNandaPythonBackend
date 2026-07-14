-- VStitch_ProductVariants: size/color/SKU/price/stock per sellable unit. Depends on VStitch_Products.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_ProductVariants (
    VstitchProductVariantId  BIGSERIAL     PRIMARY KEY,
    VstitchProductId         BIGINT        NOT NULL REFERENCES VStitch_Products(VstitchProductId) ON DELETE CASCADE,
    Sku                      VARCHAR(250)  NOT NULL,
    Size                     VARCHAR(50)   NOT NULL DEFAULT 'Standard',
    Color                    VARCHAR(50)   NOT NULL DEFAULT 'Standard',
    Price                    NUMERIC(10,2) NOT NULL CHECK (Price >= 0),
    StockQuantity            INTEGER       NOT NULL DEFAULT 0 CHECK (StockQuantity >= 0),
    IsActive                 BOOLEAN       NOT NULL DEFAULT TRUE,
    created_by               VARCHAR(250)  NOT NULL,
    created_date             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by               VARCHAR(250),
    updated_date             TIMESTAMP,

    CONSTRAINT uq_variants_sku UNIQUE (Sku),
    -- Size/Color are NOT NULL (default 'Standard' for products that don't vary
    -- by one of them) specifically so this constraint can't be bypassed by two
    -- rows both leaving a column NULL - Postgres does not treat NULL = NULL.
    CONSTRAINT uq_variants_product_size_color UNIQUE (VstitchProductId, Size, Color)
);

CREATE INDEX IF NOT EXISTS idx_variants_product_id ON VStitch_ProductVariants (VstitchProductId);
