# VStitch Admin API Reference

Base URL: `<backend host>` (same host as the customer-facing API).
All endpoints are under `/admin/*`.

## Authentication

Every endpoint below **except** `POST /admin/login` requires:

```
Authorization: Bearer <admin_access_token>
```

The token is issued by `POST /admin/login` and expires after 60 minutes
(configurable server-side). A missing, malformed, expired, or non-admin
token returns:

```json
// 401 Unauthorized
{ "detail": "Invalid or expired admin access token." }
```

## Conventions

- All list endpoints are **keyset-paginated**: pass `after_id` (the last
  `next_cursor` you received) to fetch the next page. Omit it for the first
  page. `has_more: true` means more pages exist.
- Timestamps are ISO-8601 (`created_date`).
- Money fields (`total_amount`, `price`, `revenue`, etc.) are plain numbers,
  not strings.
- Error responses are always `{ "detail": "<message>" }`. Status codes used
  throughout this API:
  - `401` - missing/invalid/expired admin token
  - `404` - the resource in the URL doesn't exist
  - `409` - conflicts with an existing resource (duplicate name/SKU)
  - `422` - the request body/query itself is invalid (bad enum value,
    missing field, out-of-range value, invalid foreign-key reference)
  - `500` / `502` - unexpected server/upstream error (message is always a
    generic, safe-to-display string, never raw internal detail)

---

## Auth

### `POST /admin/login`

No auth required (this is how you get the token).

**Request**
```json
{
  "admin_username": "vansh_admin",
  "password": "AdminPass123!"
}
```

**Response `200`**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "admin_id": 1,
  "admin_username": "vansh_admin"
}
```

**Response `401`** (wrong username or password - message is deliberately
identical for both so a caller can't enumerate valid usernames)
```json
{ "detail": "Invalid admin username or password." }
```

---

## Orders

### `GET /admin/orders`

Cross-customer order list, newest first.

**Query params** (all optional)
| Param | Type | Notes |
|---|---|---|
| `status` | string | one of `payment_pending, payment_failed, placed, confirmed, processing, shipped, out_for_delivery, delivered, cancelled, delivery_failed` |
| `payment_method` | string | `cod` or `razorpay` |
| `search` | string | matches order id (exact), customer email, or customer name (all substring/ILIKE except order id) |
| `after_id` | int | pagination cursor |
| `limit` | int | default 20, max 100 |

**Sample request**
```
GET /admin/orders?status=placed&limit=20
```

**Response `200`**
```json
{
  "orders": [
    {
      "vstitch_order_id": 27,
      "vstitch_user_id": 14,
      "customer_name": "Anjali Nanda",
      "customer_email": "anjali@example.com",
      "order_status": "placed",
      "payment_method": "cod",
      "total_amount": 2499.00,
      "shipping_recipient_name": "Anjali Nanda",
      "shipping_address_line1": "221B, MG Road",
      "shipping_address_line2": "Near Metro Station",
      "shipping_city": "Bengaluru",
      "shipping_state": "Karnataka",
      "shipping_postal_code": "560001",
      "shipping_country": "India",
      "shipping_phone_number": "9876543210",
      "awb_code": null,
      "courier_name": null,
      "created_date": "2026-07-18T10:15:32.123456",
      "items": [
        {
          "vstitch_order_item_id": 41,
          "product_name_snapshot": "Banarasi Silk Saree",
          "size_snapshot": "M",
          "color_snapshot": "Red",
          "unit_price_snapshot": 2499.00,
          "quantity": 1
        }
      ]
    }
  ],
  "has_more": true,
  "next_cursor": 27
}
```

**Response `422`** (bad `status`/`payment_method`)
```json
{ "detail": "status must be one of ('payment_pending', 'payment_failed', 'placed', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled', 'delivery_failed')." }
```

### `GET /admin/orders/{vstitch_order_id}`

Same shape as one item of the list above.

**Response `404`**
```json
{ "detail": "Order 9999 was not found." }
```

### `PATCH /admin/orders/{vstitch_order_id}/status`

Free-form admin override - any valid `OrderStatus` value is accepted from
any prior status (this is an intentional override, not a forward-pipeline
check like the customer flow uses).

**Request**
```json
{ "order_status": "shipped" }
```

**Response `200`** - the full updated order (same shape as `GET .../{id}`).

**Response `422`** (invalid status value)
```json
{ "detail": "order_status must be one of ('payment_pending', 'payment_failed', 'placed', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled', 'delivery_failed')." }
```

**Response `404`**
```json
{ "detail": "Order 9999 was not found." }
```

### `POST /admin/orders/{vstitch_order_id}/sync-status`

"Refresh status" action. Pulls the order's live status from Shiprocket (by
its AWB) and updates `order_status` in our DB if it's changed - use this
when the order screen looks stale (e.g. Shiprocket shows the parcel has
moved but our status still says `placed`/`confirmed`). Safe to call
repeatedly - a no-op if nothing changed, and it can never move an order
backwards or resurrect a cancelled/delivered one.

No request body.

**Response `200`** - the full updated order (same shape as `GET .../{id}`),
whether or not the status actually changed.

**Response `409`** (no shipment/AWB yet - nothing to sync against)
```json
{ "detail": "Order 27 has no AWB assigned yet - nothing to sync against." }
```

**Response `409`** (order doesn't exist)
```json
{ "detail": "Order 9999 was not found." }
```

**Response `502`** (Shiprocket unreachable/error)
```json
{ "detail": "Something went wrong syncing the order status from Shiprocket. Please try again later." }
```

---

## Revenue Dashboard

### `GET /admin/revenue/summary`

**Query params** (both optional, default to today)
| Param | Type |
|---|---|
| `from_date` | `YYYY-MM-DD` |
| `to_date` | `YYYY-MM-DD` |

`today_revenue`/`today_orders_count` are scoped to `[from_date, to_date]`;
`total_revenue`/`total_orders_count` are always all-time.

**Sample request**
```
GET /admin/revenue/summary?from_date=2026-07-01&to_date=2026-07-20
```

**Response `200`**
```json
{
  "today_revenue": 48250.00,
  "today_orders_count": 19,
  "total_revenue": 812430.50,
  "total_orders_count": 341,
  "pending_orders_count": 12,
  "low_stock_count": 6,
  "pending_shipments_count": 3
}
```

- `pending_orders_count` = orders in `placed`/`confirmed`/`processing`
- `low_stock_count` = active variants with `stock_quantity <= 5`
- `pending_shipments_count` = orders with a Shiprocket shipment created but
  no AWB/courier assigned yet

### `GET /admin/revenue/daily`

Same query params as above. Returns one row per calendar day that had
revenue in range.

**Response `200`**
```json
[
  { "date": "2026-07-18", "revenue": 12450.00, "orders_count": 5 },
  { "date": "2026-07-19", "revenue": 8990.00, "orders_count": 3 },
  { "date": "2026-07-20", "revenue": 26810.00, "orders_count": 11 }
]
```

---

## Categories

### `GET /admin/categories`

No query params - returns every category, including inactive ones.

**Response `200`**
```json
[
  {
    "vstitch_category_id": 1,
    "category_name": "Sarees",
    "parent_category_id": null,
    "image_url": "https://storage.example.com/categories/sarees.jpg",
    "is_active": true
  },
  {
    "vstitch_category_id": 5,
    "category_name": "Banarasi",
    "parent_category_id": 1,
    "image_url": null,
    "is_active": true
  }
]
```

### `POST /admin/categories`

**Request**
```json
{
  "category_name": "Kanjivaram",
  "parent_category_id": 1,
  "image_url": "https://storage.example.com/categories/kanjivaram.jpg"
}
```

**Response `201`** - the created category (same shape as list item).

**Response `409`** (name already used under the same parent, or as a
top-level name)
```json
{ "detail": "A category with this name already exists under the same parent." }
```

**Response `422`** (`parent_category_id` doesn't exist)
```json
{ "detail": "Parent category 999 does not exist." }
```

### `PATCH /admin/categories/{vstitch_category_id}`

All fields optional - only send what changes. Sending a field as `null`
is only valid for `parent_category_id`/`image_url` (they're genuinely
nullable); `category_name`/`is_active` reject an explicit `null`.

**Request** (partial update example)
```json
{ "is_active": false }
```

**Response `200`** - the updated category.

**Response `404`**
```json
{ "detail": "Category 999 was not found." }
```

**Response `422`** (explicit null on a required field, or bad
`parent_category_id`)
```json
{ "detail": "category_name cannot be null." }
```

### `DELETE /admin/categories/{vstitch_category_id}`

Soft delete (`is_active` set to `false` - products referencing this
category are never orphaned or blocked, `parent_category_id` uses
`ON DELETE SET NULL`).

**Response `204`** - empty body.

**Response `404`**
```json
{ "detail": "Category 999 was not found." }
```

---

## Products

### `GET /admin/products`

Includes inactive products, full variant/image detail per product.

**Query params**
| Param | Type | Notes |
|---|---|---|
| `after_id` | int | pagination cursor |
| `limit` | int | default 20, max 100 |

**Response `200`**
```json
{
  "items": [
    {
      "vstitch_product_id": 4,
      "product_name": "Banarasi Silk Saree",
      "description": "Handwoven pure silk saree with zari border.",
      "category_id": 5,
      "category_name": "Banarasi",
      "base_price": 2499.00,
      "is_active": true,
      "variants": [
        {
          "vstitch_product_variant_id": 11,
          "sku": "BSS-RED-M",
          "size": "M",
          "color": "Red",
          "price": 2499.00,
          "stock_quantity": 8,
          "is_active": true,
          "weight_kg": 0.5,
          "length_cm": 30.0,
          "breadth_cm": 20.0,
          "height_cm": 5.0
        }
      ],
      "images": [
        { "image_url": "https://storage.example.com/products/bss-red.jpg", "is_primary": true, "display_order": 0 }
      ]
    }
  ],
  "next_cursor": 8,
  "has_more": true
}
```

### `POST /admin/products`

**Batch create** - accepts multiple products in one call. Each product is
its own transaction: one bad row (duplicate SKU, invalid `category_id`, an
out-of-range shipping dimension) fails **only that product** and is
reported in `errors[]` - it never rolls back products that already
succeeded earlier in the same batch.

**Request**
```json
{
  "products": [
    {
      "product_name": "Anarkali Kurti",
      "description": "Floor-length anarkali with embroidery.",
      "category_id": 2,
      "base_price": 1899.00,
      "is_active": true,
      "variants": [
        {
          "sku": "AK-BLUE-M",
          "size": "M",
          "color": "Blue",
          "price": 1899.00,
          "stock_quantity": 15,
          "is_active": true,
          "weight_kg": 0.4,
          "length_cm": 28.0,
          "breadth_cm": 18.0,
          "height_cm": 4.0
        },
        {
          "sku": "AK-BLUE-L",
          "size": "L",
          "color": "Blue",
          "price": 1899.00,
          "stock_quantity": 10
        }
      ],
      "images": [
        { "image_url": "https://storage.example.com/products/ak-blue.jpg", "is_primary": true, "display_order": 0 }
      ]
    }
  ]
}
```
(`size`, `color` default to `"Standard"`; `stock_quantity` defaults to `0`;
`is_active` defaults to `true`; `weight_kg`/`length_cm`/`breadth_cm`/
`height_cm` are optional at creation time but required later for shipment
creation; `images` may be omitted entirely.)

**Response `201`**
```json
{
  "created": [
    { "vstitch_product_id": 9, "product_name": "Anarkali Kurti", "...": "full product shape, see GET above" }
  ],
  "errors": []
}
```

**Response `201`** (partial failure example - batch of 3, one bad row)
```json
{
  "created": [
    { "vstitch_product_id": 10, "product_name": "..." },
    { "vstitch_product_id": 11, "product_name": "..." }
  ],
  "errors": [
    { "index": 2, "message": "A variant with this SKU already exists." }
  ]
}
```
Note: the batch endpoint always returns `201` - per-item failures live in
`errors[]`, not the HTTP status.

### `PATCH /admin/products/{vstitch_product_id}`

All fields optional; explicit `null` is rejected for `product_name`,
`base_price`, `is_active` (accepted for `description`/`category_id`).

**Request**
```json
{ "base_price": 2199.00 }
```

**Response `200`** - the updated product (full shape, same as list item).

**Response `422`** (bad `category_id`)
```json
{ "detail": "Category 999 does not exist." }
```

### `DELETE /admin/products/{vstitch_product_id}`

Soft delete. **Response `204`**.

### `POST /admin/products/{vstitch_product_id}/variants`

**Request**
```json
{
  "sku": "AK-BLUE-XL",
  "size": "XL",
  "color": "Blue",
  "price": 1999.00,
  "stock_quantity": 5,
  "weight_kg": 0.4,
  "length_cm": 28.0,
  "breadth_cm": 18.0,
  "height_cm": 4.0
}
```

**Response `201`**
```json
{
  "vstitch_product_variant_id": 33,
  "sku": "AK-BLUE-XL",
  "size": "XL",
  "color": "Blue",
  "price": 1999.00,
  "stock_quantity": 5,
  "is_active": true,
  "weight_kg": 0.4,
  "length_cm": 28.0,
  "breadth_cm": 18.0,
  "height_cm": 4.0
}
```

**Response `409`** (duplicate SKU, or same product+size+color already
exists)
```json
{ "detail": "A variant with this SKU already exists." }
```

**Response `422`** (out-of-range dimensions, or product doesn't exist)
```json
{ "detail": "Invalid shipping dimensions - weight_kg must be greater than 0, and length_cm/breadth_cm/height_cm must each be at least 0.5, when provided." }
```

### `PATCH /admin/product-variants/{vstitch_product_variant_id}`

All fields optional; explicit `null` rejected for `sku`, `size`, `color`,
`price`, `stock_quantity`, `is_active` (accepted for the dimension fields).

**Request**
```json
{ "stock_quantity": 20 }
```

**Response `200`** - the updated variant (same shape as create response).

### `DELETE /admin/product-variants/{vstitch_product_variant_id}`

Soft delete (never a hard delete - would cascade-remove the variant from
every customer's live cart). **Response `204`**.

---

## Returns

### `GET /admin/returns`

**Query params**
| Param | Type | Notes |
|---|---|---|
| `status` | string | `requested, approved, rejected, picked_up, completed, cancelled` |
| `after_id` | int | pagination cursor |
| `limit` | int | default 20, max 100 |

**Response `200`**
```json
{
  "returns": [
    {
      "vstitch_return_order_id": 3,
      "vstitch_order_id": 27,
      "customer_name": "Anjali Nanda",
      "customer_email": "anjali@example.com",
      "reason": "Wrong size received",
      "status": "requested",
      "shiprocket_return_order_id": null,
      "shiprocket_shipment_id": null,
      "created_date": "2026-07-19T09:00:00.000000"
    }
  ],
  "has_more": false,
  "next_cursor": null
}
```

### `PATCH /admin/returns/{vstitch_return_order_id}/status`

Free-form override, same idea as order status.

**Request**
```json
{ "status": "approved" }
```

**Response `200`** - the updated return (same shape as list item).

**Response `422`** (invalid status)
```json
{ "detail": "status must be one of ('requested', 'approved', 'rejected', 'picked_up', 'completed', 'cancelled')." }
```

---

## Shipping Ops

Thin wrappers around Shiprocket - every response below is Shiprocket's own
response, passed through as-is (field names/shape come from Shiprocket,
not this backend). Shown values are representative, not guaranteed exact.

### `POST /admin/shipments/{vstitch_order_id}/awb`

Assigns a courier/AWB to an order that already has a Shiprocket shipment
but no AWB yet (e.g. automatic assignment failed at order-creation time).

**Response `200`** (Shiprocket pass-through, representative shape)
```json
{
  "awb_assign_status": 1,
  "response": {
    "data": {
      "awb_code": "1234567890123",
      "courier_name": "Delhivery",
      "courier_company_id": 10
    }
  }
}
```

**Response `409`**
```json
{ "detail": "Order 27 already has AWB 1234567890123 assigned - not re-assigning." }
```

### `POST /admin/shipments/pickup`
### `POST /admin/shipments/label`
### `POST /admin/shipments/manifest`
### `POST /admin/shipments/invoice`

**Request** (same shape for all four)
```json
{ "vstitch_order_ids": [27, 28, 29] }
```

**Response `200`** - Shiprocket's pass-through response (pickup
confirmation / label PDF URL / manifest URL / invoice URL, depending on
endpoint).

**Response `409`** (an order has no Shiprocket shipment/order yet)
```json
{ "detail": "Order 28 has no Shiprocket shipment yet - create it first." }
```

### `GET /admin/shipments/ndr`

No body. Returns Shiprocket's current NDR (non-delivery report) order
list, pass-through.

### `POST /admin/shipments/ndr/action`

**Request** - passed through to Shiprocket as-is (their NDR action payload
shape: `action` is `"reattempt"` or `"return"`, plus whatever per-AWB
detail their NDR docs require).
```json
{
  "ndr_action_payload": {
    "action": "reattempt",
    "awb": "1234567890123",
    "comment": "Customer confirmed availability for redelivery."
  }
}
```

**Response `200`** - Shiprocket's pass-through response.
