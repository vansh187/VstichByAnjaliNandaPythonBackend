# Coupons — Frontend Integration Guide

For the team wiring the checkout/billing screen's coupon list + "Apply
coupon" box up to the backend. Covers the two customer-facing endpoints:
`GET /coupons` and `POST /coupons/apply`. (Admin coupon management -
`/admin/coupons` - is a separate, admin-panel-only concern, not covered
here.)

**Base URL:** `https://vstichbyanjalinandapythonbackend.onrender.com`

| Method | Path | Auth |
|---|---|---|
| GET | `/coupons` | None — reachable by any visitor, logged in or not |
| POST | `/coupons/apply` | None — same as above (a guest cart can preview a coupon before login) |

---

## 1. `GET /coupons` — coupons to show on the billing screen

Returns only the coupons that are **both** switched on **and** already
usable at the given cart total — this is price-based selection, not a
static list. Call it with the current cart/order subtotal as
`order_amount` every time that total changes (item added/removed, quantity
changed), so the list on screen always reflects what's actually
applicable right now.

### Request

```
GET /coupons?order_amount=2500
```

| Query param | Type | Rules |
|---|---|---|
| `order_amount` | number | optional, defaults to `0` if omitted — pass the current cart subtotal |

### Success response — `200`

```json
{
  "items": [
    {
      "coupon_code": "FESTIVE10",
      "coupon_name": "Festive 10",
      "coupon_description": "10% off on orders above ₹2000",
      "discount_type": "percentage",
      "discount_value": 10.0,
      "min_order_amount": 2000.0
    }
  ]
}
```

`items` is `[]` (not an error) when nothing currently qualifies — e.g. cart
total below every active coupon's `min_order_amount`, or no coupons are
active at all. Render that as "no coupons available right now", not as a
failure state.

`discount_type` is either:
- `"percentage"` — `discount_value` is a percent (e.g. `10.0` = 10% off)
- `"flat"` — `discount_value` is a currency amount off (e.g. `150.0` = ₹150 off)

### Error response — `500`

```json
{ "detail": "Something went wrong while loading coupons. Please try again later." }
```

No `422`/`401` cases for this endpoint — `order_amount` is optional and
has no validation beyond "must be a number ≥ 0" (a negative number just
422s like any other malformed query param, but there's no legitimate way
to hit that from the UI since a cart total is never negative).

### UI guidance

- Fine to show `discount_value`/`discount_type` however you like (e.g.
  format `percentage` as `"10% OFF"`, `flat` as `"₹150 OFF"`) — the backend
  doesn't send a pre-formatted label.
- **This list is informational only.** Don't compute the actual discount
  amount client-side from `discount_value` — that's what `/coupons/apply`
  is for (see below). Treat this endpoint purely as "what's shown to the
  shopper," not as the source of truth for the amount actually charged.

---

## 2. `POST /coupons/apply` — apply a specific code at checkout

Call this when the shopper clicks "Apply" on a coupon (whether they picked
it from the `GET /coupons` list or typed a code in manually). Always
re-validates server-side — a coupon being visible a moment earlier doesn't
guarantee it's still active or that the threshold is still met, so never
trust a cached/earlier response for the actual discount math.

Rate-limited to **20 requests/minute per IP**.

### Request

```http
POST /coupons/apply
Content-Type: application/json

{ "coupon_code": "festive10", "order_amount": 3000 }
```

| Field | Type | Rules |
|---|---|---|
| `coupon_code` | string | required — case-insensitive, backend normalizes to uppercase |
| `order_amount` | number | required, must be `> 0` — pass the current cart subtotal |

### Success response — `200`

```json
{
  "coupon_code": "FESTIVE10",
  "discount_amount": 300.0,
  "final_amount": 2700.0,
  "message": "Coupon applied successfully."
}
```

`discount_amount` and `final_amount` are the numbers to actually show/bill
- computed server-side, already rounded to 2 decimal places. A `flat`
coupon is automatically capped at the order total (never produces a
negative `final_amount`).

### Error responses

| Status | Example `detail` | Cause | UI guidance |
|---|---|---|---|
| 404 | `"Invalid coupon code."` | no coupon exists with that code | "This coupon code doesn't exist" |
| 409 | `"This coupon is no longer active."` | coupon exists but has been switched off | "This coupon is no longer available" |
| 409 | `"This coupon requires a minimum order of 2000.00."` | cart total is below `min_order_amount` | show the message directly - it already states the threshold |
| 422 | validation error array | missing `coupon_code`, or `order_amount` missing/not a positive number | shouldn't be reachable from normal UI flow (cart total is always positive) - treat as a generic "something went wrong" if it ever happens |
| 429 | `"Too many requests - please try again shortly."` | more than 20 requests/minute from this client | "Please wait a moment and try again" |
| 500 | `"Something went wrong while applying the coupon. Please try again later."` | unexpected server/database error | generic retry message |

### Standard error shape

```json
{ "detail": "Human-readable message, safe to show or adapt for the user" }
```

**422** is the one exception — `detail` is an array of field-level
validation errors (Pydantic's default shape), same as every other endpoint:

```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "order_amount"],
      "msg": "Input should be greater than 0",
      "input": -100
    }
  ]
}
```

### UI guidance

- Disable the "Apply" button while the request is in flight — no
  server-side duplicate-submission guard, though applying the same valid
  coupon twice is harmless (same result both times, not cumulative).
- On `404`/`409`, show the returned `detail` message inline near the
  coupon input rather than a generic error - all three are written to be
  directly shopper-facing.
- On a successful apply, use `final_amount` as the new order total shown
  at checkout - don't re-derive it from `discount_value` yourself.
- If the shopper changes their cart (adds/removes items) after applying a
  coupon, re-call `/coupons/apply` with the new `order_amount` before
  final checkout - a previously-applied discount is not guaranteed to
  still be valid (they might now be below `min_order_amount` if they
  removed items).

---

*Generated from `vstitchapi/couponApi.py` and its DTOs
(`vstitchDTO/applyCouponDTO.py`, `vstitchDTO/couponResponseDTO.py`) —
Vstitch Backend. Backing table: `VSTITCH_COUPONS` (migration
`vstitchDatabase/schema/migrations/0019_add_coupons.sql`, already applied
to production).*
