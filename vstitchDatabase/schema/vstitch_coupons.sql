-- VSTITCH_COUPONS: discount codes shown on the marketing "Active Coupons"
-- screen and applied at checkout. No FK to any order/user - a coupon is a
-- standalone, reusable definition, not tied to a specific purchase.
--
-- CouponCode is what the shopper types/clicks to apply (UNIQUE, normalized
-- to uppercase at the DTO layer before it ever reaches this table). There
-- is deliberately no separate display name/description column - the admin
-- panel's coupon contract identifies a coupon purely by its code.
--
-- DiscountType is 'percentage' (DiscountValue is a 0-100 percent, enforced
-- by ck_vstitch_coupons_percentage_range) or 'flat' (DiscountValue is a
-- currency amount). MaxDiscountAmount optionally caps how much a
-- percentage coupon can discount in absolute currency terms (irrelevant
-- for 'flat', where DiscountValue already is that cap).
--
-- MinOrderAmount/ValidFrom/ValidUntil/UsageLimit/UsedCount together gate
-- whether a coupon can currently be applied: MinOrderAmount NULL means no
-- minimum; ValidFrom/ValidUntil bound an availability window (ValidUntil
-- NULL means no expiry); UsageLimit NULL means unlimited redemptions.
-- UsedCount is incremented by the checkout/order-completion flow when a
-- coupon is actually redeemed on a placed order - NOT by POST
-- /coupons/apply, which is only a preview/validation step a shopper can
-- call any number of times without ever completing a purchase.
--
-- POST /coupons/apply always re-checks IsActive, the min-order threshold,
-- the valid-from/until window, and the usage limit server-side at apply
-- time, never trusting whatever was true when the coupon list was first
-- fetched - a coupon deactivated or exhausted mid-checkout must not still
-- be honorable just because it was visible a moment earlier.
--
-- Engine: PostgreSQL. Added by migrations/0019_add_coupons.sql, redesigned
-- by migrations/0020_redesign_coupons_schema.sql.

CREATE TABLE IF NOT EXISTS VSTITCH_COUPONS (
    VstitchCouponId    BIGSERIAL      PRIMARY KEY,
    CouponCode         VARCHAR(50)    NOT NULL,
    DiscountType       VARCHAR(20)    NOT NULL,
    DiscountValue      NUMERIC(10,2)  NOT NULL,
    MinOrderAmount     NUMERIC(10,2),
    MaxDiscountAmount  NUMERIC(10,2),
    UsageLimit         INT,
    UsedCount          INT            NOT NULL DEFAULT 0,
    ValidFrom          TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ValidUntil         TIMESTAMP,
    IsActive           BOOLEAN        NOT NULL DEFAULT TRUE,
    created_by         VARCHAR(250)   NOT NULL,
    created_date       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by         VARCHAR(250),
    updated_date       TIMESTAMP,

    CONSTRAINT uq_vstitch_coupons_code UNIQUE (CouponCode),
    CONSTRAINT ck_vstitch_coupons_discount_type CHECK (DiscountType IN ('percentage', 'flat')),
    CONSTRAINT ck_vstitch_coupons_discount_value CHECK (DiscountValue > 0),
    CONSTRAINT ck_vstitch_coupons_percentage_range CHECK (DiscountType <> 'percentage' OR DiscountValue <= 100),
    CONSTRAINT ck_vstitch_coupons_min_order_amount CHECK (MinOrderAmount IS NULL OR MinOrderAmount >= 0),
    CONSTRAINT ck_vstitch_coupons_max_discount_amount CHECK (MaxDiscountAmount IS NULL OR MaxDiscountAmount > 0),
    CONSTRAINT ck_vstitch_coupons_usage_limit CHECK (UsageLimit IS NULL OR UsageLimit >= 0),
    CONSTRAINT ck_vstitch_coupons_used_count CHECK (UsedCount >= 0),
    CONSTRAINT ck_vstitch_coupons_valid_window CHECK (ValidUntil IS NULL OR ValidUntil >= ValidFrom)
);

CREATE INDEX IF NOT EXISTS idx_coupons_active_min_order ON VSTITCH_COUPONS (IsActive, MinOrderAmount);
