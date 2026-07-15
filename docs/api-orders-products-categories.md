# Vstitch API — Orders, Products & Categories

Everything beyond signup/login: placing a cash-on-delivery order, and browsing the catalog to build listing and product-detail pages.

**Base URL:** `http://<host>:<port>`

| Method | Path | Auth |
|---|---|---|
| POST | `/orders` | Required (bearer token) |
| GET | `/products` | Public |
| GET | `/products/{product_id}` | Public |
| GET | `/categories` | Public |

---

## POST /orders

Places a cash-on-delivery order. Send the JWT from `/login` as a bearer token. Validates every requested variant is active and in stock, snapshots product name/size/color/price onto the order, and decrements stock atomically.

### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request body

| Field | Type | Rules |
|---|---|---|
| `shipping_recipient_name` | string | 1–250 chars |
| `shipping_address_line1` | string | 1–250 chars |
| `shipping_address_line2` | string? | optional, max 250 chars |
| `shipping_city` | string | 1–250 chars |
| `shipping_state` | string | 1–250 chars |
| `shipping_postal_code` | string | 1–20 chars |
| `shipping_country` | string | 1–250 chars |
| `shipping_phone_number` | string | 7–250 chars |
| `items` | array | 1–50 entries, see below |

**`items[]` entry**

| Field | Type | Rules |
|---|---|---|
| `vstitch_product_variant_id` | int | > 0 — from `/products/{id}` |
| `quantity` | int | 1–100 |

### Example request

```http
POST /orders
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "shipping_recipient_name": "Anjali Nanda",
  "shipping_address_line1": "12 MG Road",
  "shipping_address_line2": "Near Central Mall",
  "shipping_city": "Mumbai",
  "shipping_state": "MH",
  "shipping_postal_code": "400001",
  "shipping_country": "India",
  "shipping_phone_number": "+919876543210",
  "items": [
    { "vstitch_product_variant_id": 12, "quantity": 2 },
    { "vstitch_product_variant_id": 27, "quantity": 1 }
  ]
}
```

### Success response — 201

```json
{
  "vstitch_order_id": 3,
  "order_status": "placed",
  "payment_method": "cod",
  "total_amount": 4497.0,
  "items": [
    {
      "vstitch_product_variant_id": 12,
      "product_name": "Anarkali Kurti",
      "size": "M",
      "color": "Blue",
      "unit_price": 1499.0,
      "quantity": 2,
      "line_total": 2998.0
    },
    {
      "vstitch_product_variant_id": 27,
      "product_name": "Bridal Lehenga Choli",
      "size": "M",
      "color": "Red",
      "unit_price": 8999.0,
      "quantity": 1,
      "line_total": 8999.0
    }
  ],
  "message": "Order placed successfully. Pay cash on delivery."
}
```

`order_status` starts at `placed` and moves through the COD pipeline: `placed → confirmed → processing → shipped → out_for_delivery → delivered`, with `cancelled` or `delivery_failed` as exit states. There is no "paid" status — cash is collected at delivery.

### Error responses

| Status | Message | Cause |
|---|---|---|
| 401 | `"Not authenticated"` / `"Invalid or expired access token."` | missing or bad bearer token |
| 409 | `"Product variant <id> is not available."` | variant doesn't exist or is inactive |
| 409 | `"Insufficient stock for <product> (<size>/<color>)."` | requested quantity exceeds live stock |
| 422 | Validation error | missing/malformed field, empty items array, quantity out of range |
| 500 | `"Something went wrong while placing the order. Please try again later."` | unexpected server error |

---

## GET /products

Paginated, filterable catalog listing for grid/browse pages. Returns lightweight cards — one price range, one image, and the set of available colors per product — not the full variant matrix. No login required.

### Query parameters

| Param | Type | Default | Notes |
|---|---|---|---|
| `category_id` | int? | — | filter to one category (from `/categories`) |
| `search` | string? | — | matches product name, max 250 chars |
| `in_stock_only` | bool | `false` | hide products with zero total stock |
| `after_id` | int? | — | cursor — omit for page 1, else pass the previous `next_cursor` |
| `limit` | int | `20` | 1–50 per page |

This is **cursor (keyset) pagination**, not page numbers — always read `next_cursor` from the response and pass it back as `after_id` to get the next page. Stop when `has_more` is `false`.

### Example requests

```
GET /products?category_id=5&in_stock_only=true&limit=2

GET /products?after_id=12&limit=2   ← next page, using the previous next_cursor
```

### Success response — 200

```json
{
  "items": [
    {
      "vstitch_product_id": 6,
      "product_name": "Banarasi Silk Saree",
      "category_id": 5,
      "category_name": "Sarees",
      "min_price": 2999.0,
      "max_price": 2999.0,
      "primary_image_url": "https://picsum.photos/seed/banarasi-silk-saree-red/600/800",
      "available_colors": ["Black", "Blue", "Golden", "Green", "Maroon", "Red"],
      "in_stock": true
    }
  ],
  "next_cursor": 6,
  "has_more": true
}
```

When `has_more` is `false`, `next_cursor` is `null` — that's the last page.

### Error responses

| Status | Message | Cause |
|---|---|---|
| 422 | Validation error | e.g. `limit=0`, `limit=9999`, `category_id=-1`, non-numeric `after_id` |
| 500 | `"Something went wrong while loading products. Please try again later."` | unexpected server error |

---

## GET /products/{product_id}

Full detail for a single product — every active size/color variant with its own price and live stock count, plus every image. Use this to render the product-detail page, and to get the `vstitch_product_variant_id` values that `/orders` expects.

### Example request

```
GET /products/6
```

### Success response — 200

```json
{
  "vstitch_product_id": 6,
  "product_name": "Banarasi Silk Saree",
  "description": "Handwoven Banarasi silk saree with a gold zari border.",
  "category_id": 5,
  "category_name": "Sarees",
  "base_price": 2999.0,
  "variants": [
    {
      "vstitch_product_variant_id": 6,
      "sku": "SAREE-BANARASI-RED-STD",
      "size": "Standard",
      "color": "Red",
      "price": 2999.0,
      "stock_quantity": 20
    }
  ],
  "images": [
    {
      "image_url": "https://picsum.photos/seed/banarasi-silk-saree-red/600/800",
      "is_primary": true,
      "display_order": 1
    }
  ]
}
```

`base_price` is catalog-display-only (e.g. a "from ₹2999" label) — always use each variant's own `price` for the actual selected size/color at checkout.

### Error responses

| Status | Message | Cause |
|---|---|---|
| 404 | `"Product <id> was not found."` | no such product, or it's inactive |
| 422 | Validation error | non-numeric `product_id` in the URL |
| 500 | `"Something went wrong while loading this product. Please try again later."` | unexpected server error |

---

## GET /categories

Flat list of active categories, for nav/filter dropdowns and the `category_id` filter on `/products`.

### Example request

```
GET /categories
```

### Success response — 200

```json
[
  { "vstitch_category_id": 9, "category_name": "Dupattas", "parent_category_id": null, "image_url": "https://picsum.photos/seed/category-dupattas/800/400" },
  { "vstitch_category_id": 6, "category_name": "Kurtis", "parent_category_id": null, "image_url": "https://picsum.photos/seed/category-kurtis/800/400" },
  { "vstitch_category_id": 7, "category_name": "Lehengas", "parent_category_id": null, "image_url": "https://picsum.photos/seed/category-lehengas/800/400" },
  { "vstitch_category_id": 8, "category_name": "Salwar Suits", "parent_category_id": null, "image_url": "https://picsum.photos/seed/category-salwar-suits/800/400" },
  { "vstitch_category_id": 5, "category_name": "Sarees", "parent_category_id": null, "image_url": "https://picsum.photos/seed/category-sarees/800/400" }
]
```

Flat, not nested — `parent_category_id` is included for when subcategories exist, but every category today is top-level (`null`). `image_url` is nullable — a category can exist before its banner artwork is uploaded, so always guard for `null` when rendering.

### Error responses

| Status | Message | Cause |
|---|---|---|
| 500 | `"Something went wrong while loading categories. Please try again later."` | unexpected server error |

---

## Notes for integration

- **Error shape:** every handled error returns FastAPI's standard `{"detail": "..."}` body. **422** responses are the one exception — `detail` is an array of field-level validation errors, not a single string.
- **Auth:** only `POST /orders` requires a bearer token. All catalog endpoints (`/products`, `/products/{id}`, `/categories`) are public — browsing never requires login.
- **Freshness:** catalog responses are cached server-side for up to 30 seconds (categories up to 120s) for speed. A product's stock/price can lag a write by up to that window — except right after it sells out to zero, which is reflected immediately. `/orders` always re-checks live stock regardless of what a cached listing showed, so a stale "in stock" card can never actually oversell.
- **Stock races:** if two people order the last unit at once, the loser gets a clean `409 Insufficient stock` on `/orders` — handle that status the same way as any other order-time validation error.

---

*Generated from `vstitchapi/orderapi.py`, `vstitchapi/productapi.py`, `vstitchapi/categoryapi.py`, and their DTOs — Vstitch Backend.*
