-- Migration: adds VSTITCH_COUPONS for the marketing "Active Coupons"
-- screen and checkout coupon-apply flow - see
-- vstitchDatabase/schema/vstitch_coupons.sql for the full rationale.
--
-- Run once, directly against Supabase (matches how 0004/0006-0018 were
-- applied - see README "Database schema").

CREATE TABLE IF NOT EXISTS VSTITCH_COUPONS (
    VstitchCouponId    BIGSERIAL      PRIMARY KEY,
    CouponName         VARCHAR(250)   NOT NULL,
    CouponCode         VARCHAR(50)    NOT NULL,
    CouponDescription  VARCHAR(500)   NOT NULL,
    DiscountType       VARCHAR(20)    NOT NULL,
    DiscountValue      NUMERIC(10,2)  NOT NULL,
    MinOrderAmount     NUMERIC(10,2)  NOT NULL DEFAULT 0,
    IsActive           BOOLEAN        NOT NULL DEFAULT TRUE,
    created_by         VARCHAR(250)   NOT NULL,
    created_date       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by         VARCHAR(250),
    updated_date       TIMESTAMP,

    CONSTRAINT uq_vstitch_coupons_code UNIQUE (CouponCode),
    CONSTRAINT ck_vstitch_coupons_discount_type CHECK (DiscountType IN ('percentage', 'flat')),
    CONSTRAINT ck_vstitch_coupons_discount_value CHECK (DiscountValue > 0),
    CONSTRAINT ck_vstitch_coupons_min_order_amount CHECK (MinOrderAmount >= 0),
    -- Defense-in-depth against a percentage coupon worth more than the
    -- order itself - the real gate is CreateCouponRequestDTO/
    -- CouponService.update_coupon's own validation, but a DB-level CHECK
    -- means this can never happen even via a direct DB write.
    CONSTRAINT ck_vstitch_coupons_percentage_range CHECK (DiscountType <> 'percentage' OR DiscountValue <= 100)
);

CREATE INDEX IF NOT EXISTS idx_coupons_active_min_order ON VSTITCH_COUPONS (IsActive, MinOrderAmount);
