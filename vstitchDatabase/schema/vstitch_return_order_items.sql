-- VStitch_ReturnOrderItems: line-item detail for a replace request (size/
-- defect issue on specific order items). Only populated for
-- VStitch_ReturnOrders rows with RequestType='replace' - a plain return has
-- no rows here (it's whole-order, see vstitch_return_orders.sql). Depends on
-- VStitch_ReturnOrders and VStitch_OrderItems. Added by
-- migrations/0010_add_delivered_date_and_replace_requests.sql.
-- Engine: PostgreSQL.

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
