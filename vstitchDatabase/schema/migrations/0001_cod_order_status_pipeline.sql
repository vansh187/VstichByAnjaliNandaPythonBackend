-- Migration: switch VStitch_Orders.OrderStatus to a cash-on-delivery pipeline
-- and add PaymentMethod. The original CHECK ('pending','paid','shipped',
-- 'delivered','cancelled','refunded') assumed upfront online payment ('paid'
-- before shipping), which doesn't fit COD - cash is only collected at the
-- delivered step. Run once, directly against Supabase (matches how the rest
-- of the schema is applied - see README "Database schema").

ALTER TABLE VStitch_Orders
    DROP CONSTRAINT vstitch_orders_orderstatus_check;

ALTER TABLE VStitch_Orders
    ALTER COLUMN OrderStatus SET DEFAULT 'placed';

ALTER TABLE VStitch_Orders
    ADD CONSTRAINT vstitch_orders_orderstatus_check
    CHECK (OrderStatus IN ('placed', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled', 'delivery_failed'));

ALTER TABLE VStitch_Orders
    ADD COLUMN PaymentMethod VARCHAR(20) NOT NULL DEFAULT 'cod' CHECK (PaymentMethod IN ('cod'));
