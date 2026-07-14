-- VStitch_Reviews: one review per (user, product) - product-level, not variant-level.
-- Depends on VStitch_Users and VStitch_Products.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_Reviews (
    VstitchReviewId    BIGSERIAL     PRIMARY KEY,
    VstitchUserId      BIGINT        NOT NULL REFERENCES VStitch_Users(VstitchUserId) ON DELETE CASCADE,
    VstitchProductId   BIGINT        NOT NULL REFERENCES VStitch_Products(VstitchProductId) ON DELETE CASCADE,
    Rating             SMALLINT      NOT NULL CHECK (Rating BETWEEN 1 AND 5),
    ReviewText         TEXT,
    created_by         VARCHAR(250)  NOT NULL,
    created_date       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by         VARCHAR(250),
    updated_date       TIMESTAMP,

    CONSTRAINT uq_reviews_user_product UNIQUE (VstitchUserId, VstitchProductId)
);

CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON VStitch_Reviews (VstitchProductId);
