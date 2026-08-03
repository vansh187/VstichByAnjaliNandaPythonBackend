-- Migration: adds VStitch_CustomizationRequests for the "Request bespoke
-- measurements" product-page form - see vstitchDatabase/schema/
-- vstitch_customization_requests.sql for the full column-by-column
-- rationale.
--
-- Run once, directly against Supabase (matches how 0004/0006/0007/0008/
-- 0009/0010/0011/0012 were applied - see README "Database schema").

CREATE TABLE IF NOT EXISTS VStitch_CustomizationRequests (
    VstitchCustomizationRequestId BIGSERIAL     PRIMARY KEY,
    VstitchProductId               BIGINT        NOT NULL REFERENCES VStitch_Products(VstitchProductId) ON DELETE RESTRICT,
    VstitchProductVariantId        BIGINT        NOT NULL REFERENCES VStitch_ProductVariants(VstitchProductVariantId) ON DELETE RESTRICT,
    VstitchUserId                  BIGINT        REFERENCES VStitch_Users(VstitchUserId) ON DELETE SET NULL,
    CustomerName                   VARCHAR(250)  NOT NULL,
    CustomerPhone                  VARCHAR(50)   NOT NULL,
    BustIn                         NUMERIC(5,2)  NOT NULL CHECK (BustIn > 0),
    WaistIn                        NUMERIC(5,2)  NOT NULL CHECK (WaistIn > 0),
    HipsIn                         NUMERIC(5,2)  NOT NULL CHECK (HipsIn > 0),
    ShoulderIn                     NUMERIC(5,2)  NOT NULL CHECK (ShoulderIn > 0),
    SleeveLengthIn                 NUMERIC(5,2)  NOT NULL CHECK (SleeveLengthIn > 0),
    DressLengthIn                  NUMERIC(5,2)  NOT NULL CHECK (DressLengthIn > 0),
    Notes                          VARCHAR(500),
    Status                         VARCHAR(20)   NOT NULL DEFAULT 'pending'
                                        CHECK (Status IN ('pending', 'in_review', 'confirmed', 'completed', 'cancelled')),
    created_by                     VARCHAR(250)  NOT NULL,
    created_date                   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by                     VARCHAR(250),
    updated_date                   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customization_requests_product_id ON VStitch_CustomizationRequests (VstitchProductId);
CREATE INDEX IF NOT EXISTS idx_customization_requests_variant_id ON VStitch_CustomizationRequests (VstitchProductVariantId);
CREATE INDEX IF NOT EXISTS idx_customization_requests_user_id ON VStitch_CustomizationRequests (VstitchUserId);
