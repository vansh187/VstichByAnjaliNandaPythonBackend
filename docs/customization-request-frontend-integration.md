# Customization / Bespoke Fit Request — Frontend Integration Guide

For the team wiring `src/components/CustomizationModal.jsx`'s submit up to
the backend instead of the WhatsApp-only flow. Covers the two new
endpoints: `POST /products/{product_id}/variants/{variant_id}/customization-requests`
and `GET /customization-requests`.

**Base URL:** `https://vstichbyanjalinandapythonbackend.onrender.com`

| Method | Path | Auth |
|---|---|---|
| POST | `/products/{vstitch_product_id}/variants/{vstitch_product_variant_id}/customization-requests` | **Optional** — works with or without a bearer token |
| GET | `/customization-requests` | Required (bearer token) |

---

## 1. `POST /products/{vstitch_product_id}/variants/{vstitch_product_variant_id}/customization-requests` — submit a bespoke request

Submits the form for the exact product + variant (size/color) the shopper
was viewing. **No login required** — the product page itself doesn't
require an account, so this endpoint must keep working for a logged-out
shopper. If a valid bearer token *is* sent, the request is attached to that
user's account (so it can later show up in `GET /customization-requests`);
if omitted, it's saved anonymously. Rate-limited to **5 requests/minute per
IP**.

### Path parameters

| Param | Type | Rules |
|---|---|---|
| `vstitch_product_id` | int | > 0 — the product being viewed |
| `vstitch_product_variant_id` | int | > 0 — the exact size/color variant selected on the page |

### Headers

```
Content-Type: application/json
Authorization: Bearer <access_token>   # optional — omit entirely if the shopper isn't logged in
```

Don't send a garbled/placeholder `Authorization` header "just in case" —
if a header is present at all, it's held to the same standard as every
other authenticated endpoint (see error table below). Only *omitting* the
header entirely gets treated as anonymous.

### Request body

| Field | Type | Rules |
|---|---|---|
| `customer_name` | string | 1–250 chars, can't be blank/whitespace-only |
| `customer_phone` | string | 7–50 chars, can't be blank/whitespace-only, not format-validated beyond that |
| `bust_in` | number | 0.1–100 (inches) |
| `waist_in` | number | 0.1–100 |
| `hips_in` | number | 0.1–100 |
| `shoulder_in` | number | 0.1–100 |
| `sleeve_length_in` | number | 0.1–100 |
| `dress_length_in` | number | 0.1–100 |
| `notes` | string? | optional, max 500 chars |

**Note on precision:** measurements are rounded server-side to 2 decimal
places (e.g. `34.567` is stored/returned as `34.57`). Fine for a
measurements form, but don't be surprised if the value you get back in the
response doesn't match what was typed to the third decimal.

### Example request — logged in

```http
POST /products/42/variants/317/customization-requests
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "customer_name": "Anjali Sharma",
  "customer_phone": "+91 98765 43210",
  "bust_in": 36,
  "waist_in": 30,
  "hips_in": 39,
  "shoulder_in": 14.5,
  "sleeve_length_in": 22,
  "dress_length_in": 42,
  "notes": "Slightly looser through the waist, please."
}
```

### Example request — logged out (no `Authorization` header at all)

```http
POST /products/42/variants/317/customization-requests
Content-Type: application/json

{
  "customer_name": "Anjali Sharma",
  "customer_phone": "+91 98765 43210",
  "bust_in": 36,
  "waist_in": 30,
  "hips_in": 39,
  "shoulder_in": 14.5,
  "sleeve_length_in": 22,
  "dress_length_in": 42
}
```

### Success response — 201

```json
{
  "vstitch_customization_request_id": 101,
  "vstitch_product_id": 42,
  "vstitch_product_variant_id": 317,
  "status": "pending",
  "created_at": "2026-08-03T10:15:00.123456"
}
```

- `vstitch_customization_request_id` — show this to the customer as a
  confirmation reference ("Request #101 submitted").
- `status` is always `"pending"` on creation. There's no
  webhook/notification when studio staff move it forward
  (`in_review` → `confirmed` → `completed`, or `cancelled`) — if the UI
  needs to reflect that later, poll `GET /customization-requests` (logged-in
  users only, see below).

### Error responses

| Status | Example `detail` | Cause |
|---|---|---|
| 401 | `"Invalid or expired access token."` | an `Authorization` header **was sent** but is malformed, expired, or otherwise invalid — this is the one case where omitting the header entirely would have succeeded anonymously instead |
| 404 | `"Product 42 / variant 999 was not found."` | `vstitch_product_id`/`vstitch_product_variant_id` don't exist, or the variant doesn't belong to that product (same message for all three cases, by design — don't try to distinguish) |
| 422 | validation error array | missing/blank required field, a measurement outside 0.1–100, or a field over its max length |
| 429 | `"Too many requests - please try again shortly."` | more than 5 requests/minute from this client — **disable the submit button after click** to avoid this on an accidental double-submit |
| 500 | `"Something went wrong while submitting your customization request. Please try again later."` | unexpected server-side failure — safe to let the customer retry |

**UI guidance:**
- Disable the submit button immediately on click, same as any other form —
  there's no server-side duplicate-submission guard here (unlike
  return/replace), so a double-click produces two rows.
- Keep the WhatsApp link as a secondary "message us directly" option, per
  the original spec — this endpoint doesn't replace it, it replaces the
  *primary* submit action.

---

## 2. `GET /customization-requests` — a shopper's own request history

Returns every customization request the **logged-in** user has submitted,
newest first. For a future "My Customization Requests" section under My
Orders — not required for the initial submit-form integration, but wired up
now in case you want it.

Requires a valid bearer token — there is no way to fetch these
anonymously (a request submitted while logged out won't show up here
either, since it has no `vstitch_user_id` to match against).

### Example request

```http
GET /customization-requests
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Success response — 200

```json
{
  "requests": [
    {
      "vstitch_customization_request_id": 101,
      "vstitch_product_id": 42,
      "vstitch_product_variant_id": 317,
      "product_name": "Black Floral Embroidered Co-ord Set",
      "size": "Standard",
      "color": "Black",
      "customer_name": "Anjali Sharma",
      "customer_phone": "+91 98765 43210",
      "bust_in": 36.0,
      "waist_in": 30.0,
      "hips_in": 39.0,
      "shoulder_in": 14.5,
      "sleeve_length_in": 22.0,
      "dress_length_in": 42.0,
      "notes": "Slightly looser through the waist, please.",
      "status": "pending",
      "created_at": "2026-08-03T10:15:00.123456"
    }
  ]
}
```

No pagination today — every request the user has ever submitted comes back
in one call. Fine for the expected volume of a bespoke-request feature; flag
it if that assumption ever changes.

### Error responses

| Status | Example `detail` | Cause |
|---|---|---|
| 401 | `"Not authenticated"` / `"Invalid or expired access token."` | missing or bad bearer token |
| 500 | `"Something went wrong while loading your customization requests. Please try again later."` | unexpected server-side failure |

---

## 3. Standard error shape (applies to both endpoints)

Every handled error returns FastAPI's standard body:

```json
{ "detail": "Human-readable message, safe to show or adapt for the user" }
```

**422** is the one exception — `detail` is an array of field-level
validation errors (Pydantic's default shape), not a single string:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "bust_in"],
      "msg": "Input should be greater than or equal to 0.1",
      "input": 0
    }
  ]
}
```

---

## 4. Quick reference: full submit flow

```
1. Shopper is on a product page, has selected a size/color (a variant id
   is already known/selected on the page).

2. Shopper fills the "Request bespoke measurements" form and hits submit.
   → POST /products/{product_id}/variants/{variant_id}/customization-requests
     - Include Authorization header ONLY if the shopper is logged in.
     - Body: customer_name, customer_phone, six measurements, optional notes.

3a. 201 → show a confirmation (e.g. "Request #101 submitted - our studio
    will reach out to confirm"). Keep the WhatsApp link visible as a
    secondary contact option.

3b. 404 → shouldn't normally happen from a real product page (would mean
    the product/variant id sent doesn't match what's actually displayed) -
    treat as a bug report if seen, not a user-facing error state.

3c. 422 → surface the specific field error(s) inline on the form.

3d. 429 → the 5/minute rate limit was hit - show a brief "please wait a
    moment and try again" message.
```

---

*Generated from `vstitchapi/customizationRequestApi.py` and its DTOs
(`vstitchDTO/customizationRequestDTO.py`,
`vstitchDTO/customizationResponseDTO.py`) — Vstitch Backend. Backing table:
`VStitch_CustomizationRequests` (migration
`vstitchDatabase/schema/migrations/0013_add_customization_requests.sql`,
already applied to production).*
