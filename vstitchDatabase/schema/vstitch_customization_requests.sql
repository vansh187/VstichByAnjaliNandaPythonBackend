-- VStitch_CustomizationRequests: one row per "Request bespoke measurements"
-- submission from a product page - tied to the exact product + variant
-- (size/color) the shopper was viewing. Reachable while logged out (the
-- product page itself requires no login), so VstitchUserId is nullable and
-- only populated when a valid bearer token was sent alongside the request.
-- Depends on VStitch_Products, VStitch_ProductVariants, VStitch_Users.
-- Engine: PostgreSQL. Added by
-- migrations/0013_add_customization_requests.sql.

CREATE TABLE IF NOT EXISTS VStitch_CustomizationRequests (
    VstitchCustomizationRequestId BIGSERIAL     PRIMARY KEY,
    -- RESTRICT, not CASCADE/SET NULL: an admin deleting a product/variant
    -- that still has an open bespoke request should have to resolve that
    -- request first, rather than the request silently losing what it was
    -- actually asking to customize.
    VstitchProductId               BIGINT        NOT NULL REFERENCES VStitch_Products(VstitchProductId) ON DELETE RESTRICT,
    VstitchProductVariantId        BIGINT        NOT NULL REFERENCES VStitch_ProductVariants(VstitchProductVariantId) ON DELETE RESTRICT,
    -- Nullable: the shopper may not be logged in when submitting - see the
    -- table comment above.
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
