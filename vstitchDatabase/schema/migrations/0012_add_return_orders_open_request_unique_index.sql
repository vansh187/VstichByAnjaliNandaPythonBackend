-- Migration: closes a TOCTOU race in the return/replace duplicate-request
-- guard. _assert_no_open_return_request (shipmentService.py) was a plain
-- SELECT-then-decide check with nothing backing it at the DB level, so two
-- near-simultaneous requests for the same order could both pass the check
-- before either had inserted its row, resulting in two Shiprocket
-- return-pickup shipments filed for one order. This partial unique index
-- makes "at most one open (not rejected/cancelled/completed) return/replace
-- request per order" an actual DB-enforced invariant - the second concurrent
-- INSERT now fails with a UniqueViolation instead of silently succeeding,
-- which OrderPersistence.create_return_order/create_replace_request catch
-- and translate into a friendly ValueError (-> 409).
--
-- Run once, directly against Supabase (matches how 0004/.../0010/0011 were
-- applied - see README "Database schema").

CREATE UNIQUE INDEX IF NOT EXISTS uq_return_orders_open_per_order
    ON VStitch_ReturnOrders (VstitchOrderId)
    WHERE Status NOT IN ('rejected', 'cancelled', 'completed');
