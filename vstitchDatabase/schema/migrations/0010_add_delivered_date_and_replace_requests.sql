-- Migration: adds VStitch_Orders.DeliveredDate so return/replace eligibility
-- (7 days since delivery) can be computed server-side from a trustworthy
-- timestamp instead of the generic updated_date column, which gets
-- overwritten by ANY later status transition. Also extends
-- VStitch_ReturnOrders to distinguish a plain return from a replace request
-- (RequestType) and adds VStitch_ReturnOrderItems so a request can be scoped
-- to specific order line items - the existing whole-order return flow keeps
-- working with zero item rows (NULL/empty = "whole order").
--
-- Run once, directly against Supabase (matches how 0004/0006/0007/0008/0009
-- were applied - see README "Database schema").

ALTER TABLE VStitch_Orders
    ADD COLUMN IF NOT EXISTS DeliveredDate TIMESTAMP NULL;

ALTER TABLE VStitch_ReturnOrders
    ADD COLUMN IF NOT EXISTS RequestType VARCHAR(20) NOT NULL DEFAULT 'return'
        CHECK (RequestType IN ('return', 'replace'));

CREATE TABLE IF NOT EXISTS VStitch_ReturnOrderItems (
    VstitchReturnOrderItemId BIGSERIAL     PRIMARY KEY,
    VstitchReturnOrderId     BIGINT        NOT NULL REFERENCES VStitch_ReturnOrders(VstitchReturnOrderId) ON DELETE CASCADE,
    VstitchOrderItemId       BIGINT        NOT NULL REFERENCES VStitch_OrderItems(VstitchOrderItemId) ON DELETE RESTRICT,
    Quantity                 INTEGER       NOT NULL CHECK (Quantity > 0),
    IssueCategory            VARCHAR(20)   NOT NULL CHECK (IssueCategory IN ('size_issue', 'defect')),
    created_by               VARCHAR(250)  NOT NULL,
    created_date             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_return_order_items_return_order_id ON VStitch_ReturnOrderItems (VstitchReturnOrderId);
CREATE INDEX IF NOT EXISTS idx_return_order_items_order_item_id ON VStitch_ReturnOrderItems (VstitchOrderItemId);
