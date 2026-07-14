-- VStitch_Products: core catalog product info. Depends on VStitch_Categories.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_Products (
    VstitchProductId   BIGSERIAL     PRIMARY KEY,
    ProductName        VARCHAR(250)  NOT NULL,
    Description        TEXT,
    VstitchCategoryId  BIGINT        REFERENCES VStitch_Categories(VstitchCategoryId) ON DELETE SET NULL,
    -- Display-only "from ₹X" price for listing/search cards before a variant is
    -- picked. Never authoritative - cart, checkout, and order math must always
    -- read the chosen VStitch_ProductVariants.Price, never this column.
    BasePrice          NUMERIC(10,2) NOT NULL CHECK (BasePrice >= 0),
    IsActive           BOOLEAN       NOT NULL DEFAULT TRUE,
    created_by         VARCHAR(250)  NOT NULL,
    created_date       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by         VARCHAR(250),
    updated_date       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON VStitch_Products (VstitchCategoryId);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON VStitch_Products (IsActive);
CREATE INDEX IF NOT EXISTS idx_products_name ON VStitch_Products (ProductName);
