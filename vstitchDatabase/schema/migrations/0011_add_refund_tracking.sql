-- Migration: adds refund tracking to VStitch_PaymentTransactions so a return/
-- replace that reaches 'completed' can trigger a Razorpay refund and have its
-- outcome reconciled via the existing /payments/webhook route. Introduces an
-- intermediate 'refund_pending' PaymentStatus between 'captured' and
-- 'refunded' (already a valid value that nothing previously set) so a refund
-- request that's in flight at Razorpay is distinguishable from one that's
-- confirmed complete.
--
-- Run once, directly against Supabase (matches how 0004/0006/0007/0008/0009/
-- 0010 were applied - see README "Database schema").

ALTER TABLE VStitch_PaymentTransactions
    ADD COLUMN IF NOT EXISTS RazorpayRefundId VARCHAR(250),
    ADD COLUMN IF NOT EXISTS RefundedAmount NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS RefundedAt TIMESTAMP;

-- Widen the existing PaymentStatus CHECK to add 'refund_pending'. Postgres
-- auto-names an inline CHECK as "<table>_<column>_check" (lowercased) - if
-- this constraint was ever renamed manually, adjust the name below to match
-- before running.
ALTER TABLE VStitch_PaymentTransactions DROP CONSTRAINT IF EXISTS vstitch_paymenttransactions_paymentstatus_check;
ALTER TABLE VStitch_PaymentTransactions ADD CONSTRAINT vstitch_paymenttransactions_paymentstatus_check
    CHECK (PaymentStatus IN ('created', 'authorized', 'captured', 'failed', 'refund_pending', 'refunded'));
