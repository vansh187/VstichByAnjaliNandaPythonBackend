-- Migration: redesigns VSTITCH_COUPONS (added by migrations/0019_add_coupons.sql)
-- to match the marketing team's actual admin-panel contract:
--   - Drops CouponName/CouponDescription - the contract has no
--     human-readable name/description at all, just CouponCode.
--   - Adds MaxDiscountAmount (caps a percentage discount's ₹ value),
--     UsageLimit/UsedCount (total redemptions allowed / consumed so far -
--     UsedCount is incremented by the checkout/order flow on redemption,
--     NOT by POST /coupons/apply, which is only a preview/validation step
--     a shopper can call repeatedly without ever completing an order),
--     ValidFrom/ValidUntil (an explicit availability window, replacing the
--     implicit "exists = available" assumption).
--   - MinOrderAmount becomes nullable: "no minimum" is now representable
--     as NULL rather than the previous DEFAULT 0.
--
-- No production coupon data existed at the time of this migration (the
-- only rows ever inserted were this feature's own now-deleted test rows),
-- so this is a plain ALTER rather than a data-preserving transform.
--
-- Run once, directly against Supabase (matches how 0004/0006-0019 were
-- applied - see README "Database schema").

ALTER TABLE VSTITCH_COUPONS
    DROP COLUMN IF EXISTS CouponName,
    DROP COLUMN IF EXISTS CouponDescription;

ALTER TABLE VSTITCH_COUPONS
    ALTER COLUMN MinOrderAmount DROP NOT NULL,
    ALTER COLUMN MinOrderAmount DROP DEFAULT;

ALTER TABLE VSTITCH_COUPONS
    ADD COLUMN IF NOT EXISTS MaxDiscountAmount NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS UsageLimit         INT,
    ADD COLUMN IF NOT EXISTS UsedCount          INT       NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ValidFrom          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS ValidUntil         TIMESTAMP;

ALTER TABLE VSTITCH_COUPONS
    DROP CONSTRAINT IF EXISTS ck_vstitch_coupons_min_order_amount,
    ADD CONSTRAINT ck_vstitch_coupons_min_order_amount CHECK (MinOrderAmount IS NULL OR MinOrderAmount >= 0),
    ADD CONSTRAINT ck_vstitch_coupons_max_discount_amount CHECK (MaxDiscountAmount IS NULL OR MaxDiscountAmount > 0),
    ADD CONSTRAINT ck_vstitch_coupons_usage_limit CHECK (UsageLimit IS NULL OR UsageLimit >= 0),
    ADD CONSTRAINT ck_vstitch_coupons_used_count CHECK (UsedCount >= 0),
    ADD CONSTRAINT ck_vstitch_coupons_valid_window CHECK (ValidUntil IS NULL OR ValidUntil >= ValidFrom);
