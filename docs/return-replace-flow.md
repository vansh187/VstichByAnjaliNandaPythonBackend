# Return / Replace / Refund flow

Covers the customer return flow, the size/defect replace flow, and the
Razorpay refund that follows a completed return/replace. All three share the
same `VStitch_ReturnOrders` table and the same Shiprocket return-pickup
mechanics (pickup from the customer's delivered address, deliver to the
warehouse).

## 1. Eligibility: 7 days since delivery

`VStitch_Orders.DeliveredDate` is stamped exactly once, the first time an
order's status transitions to `delivered` - via `update_order_status_guarded`
(the Shiprocket tracking webhook / `sync_order_status_from_shiprocket` path)
or `update_order_status_admin` (a manual admin override). Both use
`COALESCE(DeliveredDate, CURRENT_TIMESTAMP)`, so a later status change never
overwrites the original delivery timestamp.

A customer can request a return or replace once `CURRENT_TIMESTAMP >=
DeliveredDate + 7 days`. This is computed **server-side in SQL** (not in
application code), to avoid clock-skew between the app server and the DB.

- `GET /orders` (My Orders) surfaces `delivered_date`, `can_return`, and
  `can_replace` per order, so the frontend can show/hide the Return/Replace
  buttons. **These flags are informational only** - every mutating request
  (`POST /orders/{id}/return`, `POST /orders/{id}/replace`) re-validates
  eligibility itself from a fresh DB read, so a stale flag or a
  directly-called API can never bypass the 7-day floor.
- **No upper bound** is enforced (only the 7-day floor) - a return/replace
  request can be filed at any point after that. This was an explicit scope
  decision; add a cutoff later if product/ops wants one.

## 2. Return flow (whole order)

1. Customer: `POST /orders/{id}/return` (`{"reason": "..."}"`, `10/minute`
   rate limit).
2. `ShipmentService.create_return`:
   - Confirms the requesting user owns the order (`_get_owned_order_for_tracking`).
   - Confirms `order_status == delivered`.
   - Confirms the 7-day eligibility gate (`_assert_return_replace_eligible`).
   - Confirms no other return/replace is already open on this order
     (`_assert_no_open_return_request` - a second request while one is
     `requested`/`approved`/`picked_up` is rejected with 409).
   - Builds a Shiprocket adhoc-order payload from the whole order, swaps
     pickup/delivery (`_swap_to_return_pickup_shape`: customer's address
     becomes pickup, `VStitch Warehouse` becomes the delivery destination),
     and calls Shiprocket's `POST /orders/create/return`.
   - Inserts a `VStitch_ReturnOrders` row (`RequestType='return'`,
     `Status='requested'`) with Shiprocket's returned order/shipment ids.
3. Admin manages it via `GET /admin/returns` / `PATCH /admin/returns/{id}/status`.

## 3. Replace flow (size/defect, item-level)

1. Customer: `POST /orders/{id}/replace` (`{"issue_category": "size_issue"|
   "defect", "reason": "...", "items": [{"vstitch_order_item_id": ..., 
   "quantity": ...}, ...]}`, `10/minute` rate limit).
2. `ShipmentService.create_replace`: same ownership/delivered/eligibility/
   duplicate-request checks as return, **plus** an item-level IDOR guard -
   every requested `vstitch_order_item_id` must belong to this order (same
   "not found" message whether it doesn't exist at all or belongs to someone
   else's order), and requested quantity is capped at what was actually
   ordered.
3. Builds the same kind of Shiprocket return-pickup shipment, but scoped to
   only the requested items (the order's item list is filtered before
   building the payload).
4. Inserts a `VStitch_ReturnOrders` row (`RequestType='replace'`) **and**
   matching `VStitch_ReturnOrderItems` rows (one per requested item, with its
   quantity and `IssueCategory`).
5. **Shipping the replacement item back out is a manual ops step** - once the
   returned item is picked up and verified, ops places a new order through
   the existing order-creation flow. This is not automated in this pass.

## 4. Refund (Razorpay)

Refund is triggered when an admin moves a return/replace to **`completed`**
via the existing `PATCH /admin/returns/{id}/status` - i.e. after the item has
actually been picked up and verified, not the moment the customer files the
request. No new endpoint is involved.

1. `AdminReturnService.update_return_status` persists the status change as
   always, then - only if the new status is `completed` and the update
   actually matched a row - calls `PaymentService.refund_order_payment`
   inside its own `try/except`. A refund failure **never** fails the status
   update itself; the response includes `refund_triggered: bool` so ops
   knows whether to retry manually (re-`PATCH ... completed` again).
2. `refund_order_payment`:
   - Looks up the order's `captured` payment transaction
     (`find_captured_transaction_by_order_id`) - raises if there is none
     (COD order, not yet captured, or already refunded/in flight).
   - Calls `RazorpayClient.refund_payment` for the full originally-captured
     amount (always read server-side, never client-supplied).
   - Moves `VStitch_PaymentTransactions.PaymentStatus`: `captured ->
     refund_pending` (guarded; a concurrent duplicate trigger is a safe no-op).
3. Razorpay processes the refund asynchronously and calls the **existing**
   `POST /payments/webhook` (same raw-body HMAC signature verification, same
   event-fingerprint idempotency as every other webhook event) with
   `refund.processed` or `refund.failed`:
   - `refund.processed` -> `refund_pending -> refunded`, stamps
     `RefundedAmount`/`RefundedAt`.
   - `refund.failed` -> `refund_pending -> captured` (reverts so it's
     retryable), stamps `FailureReason`.

## 5. Database schema (migrations 0010, 0011)

- `VStitch_Orders.DeliveredDate TIMESTAMP` - see section 1.
- `VStitch_ReturnOrders.RequestType VARCHAR(20) CHECK IN ('return', 'replace')`.
- `VStitch_ReturnOrderItems` (new table): `VstitchReturnOrderId` FK,
  `VstitchOrderItemId` FK, `Quantity`, `IssueCategory CHECK IN ('size_issue',
  'defect')`.
- `VStitch_PaymentTransactions`: `RazorpayRefundId`, `RefundedAmount`,
  `RefundedAt`; `PaymentStatus` CHECK widened to add `'refund_pending'`.

## 6. Admin: `request_type` filter

`GET /admin/returns?request_type=replace` (or `return`) filters the list;
omitting it returns both. `PATCH /admin/returns/{id}/status` is unchanged in
shape and handles both return and replace rows identically - `RequestType`
itself is never mutated by a status update.

## 7. Known limitations (deferred, not fixed in this pass)

- **No upper bound** on the return/replace window - only the 7-day floor.
- **Warehouse destination address gap**: the Shiprocket return-pickup
  payload's `shipping_address` (the delivery destination for the pickup) is
  only a location-name string (`self.pickup_location`) - there's no city/
  state/pincode override for the warehouse side. This predates this feature
  (it already existed in `create_return`) and affects both return and
  replace identically; left as-is here.
- Replacing the returned item with a new one is a manual ops step, not an
  automated outbound shipment.
