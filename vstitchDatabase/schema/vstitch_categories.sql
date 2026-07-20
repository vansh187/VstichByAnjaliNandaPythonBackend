-- VStitch_Categories: self-referencing category tree for the (women's-only) catalog.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_Categories (
    VstitchCategoryId  BIGSERIAL     PRIMARY KEY,
    CategoryName       VARCHAR(250)  NOT NULL,
    ParentCategoryId   BIGINT        REFERENCES VStitch_Categories(VstitchCategoryId) ON DELETE SET NULL,
    -- One banner/thumbnail image per category, stored as a Supabase Storage URL
    -- (not binary data), same convention as VStitch_ProductImages.ImageUrl.
    -- Nullable: a category can exist before its artwork is ready. A single
    -- column, not a separate table, because a category needs exactly one
    -- representative image, unlike products which need many (per variant).
    ImageUrl           VARCHAR(500),
    IsActive           BOOLEAN       NOT NULL DEFAULT TRUE,
    created_by         VARCHAR(250)  NOT NULL,
    created_date       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by         VARCHAR(250),
    updated_date       TIMESTAMP,

    CONSTRAINT uq_categories_name_parent UNIQUE (CategoryName, ParentCategoryId)
);

CREATE INDEX IF NOT EXISTS idx_categories_parent_category_id ON VStitch_Categories (ParentCategoryId);

-- Postgres treats NULL <> NULL, so the UNIQUE constraint above does not stop two
-- top-level categories (ParentCategoryId IS NULL) sharing the same name. Cover
-- that case with a partial unique index instead of leaving it open.
CREATE UNIQUE INDEX IF NOT EXISTS uq_categories_name_top_level ON VStitch_Categories (CategoryName) WHERE ParentCategoryId IS NULL;
