-- VSTITCH_COUPONS: discount codes shown on the marketing "Active Coupons"
-- screen and applied at checkout. No FK to any order/user - a coupon is a
-- standalone, reusable definition, not tied to a specific purchase.
--
-- CouponCode is what the shopper types/clicks to apply (UNIQUE, normalized
-- to uppercase at the DTO layer before it ever reaches this table) -
-- distinct from CouponName, which is just the admin-facing display label.
--
-- DiscountType/DiscountValue/MinOrderAmount together drive price-based
-- selection: GET /coupons?order_amount=<cart total> only returns
-- IsActive=TRUE rows whose MinOrderAmount the cart total actually meets
-- (e.g. "order above 2000 -> 10% off"). DiscountType is 'percentage'
-- (DiscountValue is a 0-100 percent, enforced by
-- ck_vstitch_coupons_percentage_range below) or 'flat' (DiscountValue is a
-- currency amount).
--
-- IsActive is the on/off switch: POST /coupons/apply always re-checks it
-- (and MinOrderAmount) server-side at apply time, never trusting whatever
-- was true when the coupon list was first fetched - a coupon deactivated
-- mid-checkout must not still be honorable just because it was visible a
-- moment earlier.
--
-- Engine: PostgreSQL. Added by migrations/0019_add_coupons.sql.

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
    CONSTRAINT ck_vstitch_coupons_percentage_range CHECK (DiscountType <> 'percentage' OR DiscountValue <= 100)
);

CREATE INDEX IF NOT EXISTS idx_coupons_active_min_order ON VSTITCH_COUPONS (IsActive, MinOrderAmount);
