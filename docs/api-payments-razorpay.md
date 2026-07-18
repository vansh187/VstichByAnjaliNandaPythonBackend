# Vstitch API — Razorpay Payments (Checkout.js)

Online checkout, as an alternative to `POST /orders` (cash on delivery). Two calls on your side: create the payment order, then open Razorpay Checkout with what it returns. Razorpay tells our backend directly whether the payment succeeded — you don't need to report success/failure yourself.

**Base URL:** `http://<host>:<port>`

| Method | Path | Auth |
|---|---|---|
| POST | `/payments/orders` | Required (bearer token) |
| POST | `/payments/webhook` | None — called by Razorpay, not by your frontend |

---

## The flow, end to end

1. User fills the checkout form and clicks **Proceed to Pay**.
2. Frontend calls `POST /payments/orders` with the same shipping + items payload as `POST /orders`.
3. Backend validates stock/pricing, creates a Razorpay order, decrements stock, and creates our own order at status `payment_pending`. It returns everything Checkout.js needs.
4. Frontend opens Razorpay Checkout using that response. The user pays (or cancels/fails) inside Razorpay's UI.
5. Razorpay calls our webhook directly — **not through your frontend** — to report the outcome. Our backend updates the order to `placed` (success) or `payment_failed` (failure, stock automatically restored) before Checkout's own callback even fires on the frontend.
6. Frontend's Checkout `handler`/`ondismiss` callbacks are for **UX only** (show a spinner, redirect to an order-confirmation or order-history page). Don't treat the client-side callback as the source of truth for whether the payment succeeded — always reflect the *current* status by polling `GET /orders` (see below), since the webhook is what actually confirms payment, and it can arrive slightly before or after Checkout's own callback.

```
┌──────────┐   1. Proceed to Pay    ┌──────────┐
│ Frontend │ ─────────────────────▶ │ Backend  │
│          │  POST /payments/orders │          │──▶ creates Razorpay order,
│          │ ◀───────────────────── │          │    decrements stock,
│          │  razorpay_order_id,    │          │    order = payment_pending
│          │  key_id, amount        └──────────┘
│          │
│          │   2. Open Checkout.js with the above
│          │ ─────────────────────▶ [Razorpay-hosted payment UI]
│          │
│          │                        Razorpay ──▶ POST /payments/webhook ──▶ Backend
│          │                                      (signed, server-to-server)
│          │                                      order = placed / payment_failed
│          │
│          │  3. handler/ondismiss fires (UX only) - then poll GET /orders
│          │     to confirm the real, webhook-driven status
└──────────┘
```

---

## POST /payments/orders

Send the JWT from `/login` as a bearer token. Same request body as `POST /orders` — see that doc for the full field table. On success, stock is already decremented and held for this order (same as COD), so don't call `POST /orders` again for the same basket.

### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Example request

```http
POST /payments/orders
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
  "vstitch_order_id": 14,
  "razorpay_order_id": "order_TEvs8RaztANrS6",
  "razorpay_key_id": "rzp_test_T1zk1Vc5lQdCNb",
  "amount": 899900,
  "currency": "INR"
}
```

`amount` is in **paise** (smallest currency unit) — that's what Checkout.js expects directly, no conversion needed. `razorpay_key_id` is Razorpay's public key id, safe to expose to the browser (it's not a secret).

### Error responses

| Status | Message | Cause |
|---|---|---|
| 401 | `"Not authenticated"` / `"Invalid or expired access token."` | missing or bad bearer token |
| 409 | `"Product variant <id> is not available."` | variant doesn't exist or is inactive |
| 409 | `"Insufficient stock for <product> (<size>/<color>)."` | requested quantity exceeds live stock |
| 422 | Validation error | missing/malformed field, empty items array, quantity out of range |
| 502 | `"Something went wrong while starting your payment. Please try again."` | Razorpay unreachable/rejected the request, or an unexpected server error |

A `502` here means **nothing was charged and no stock was held** — safe to let the user retry immediately.

---

## Opening Razorpay Checkout

Load Checkout.js once (usually in your HTML `<head>` or on the checkout page):

```html
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
```

Then, using the response from `POST /payments/orders`:

```js
async function payWithRazorpay(shippingAndItemsPayload, accessToken) {
  const res = await fetch("/payments/orders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(shippingAndItemsPayload),
  });

  if (!res.ok) {
    const error = await res.json();
    // Show error.detail to the user - nothing was charged, safe to retry.
    throw new Error(error.detail || "Could not start payment.");
  }

  const payment = await res.json();

  const options = {
    key: payment.razorpay_key_id,
    amount: payment.amount,
    currency: payment.currency,
    order_id: payment.razorpay_order_id,
    name: "Vstitch",
    prefill: {
      name: shippingAndItemsPayload.shipping_recipient_name,
      contact: shippingAndItemsPayload.shipping_phone_number,
    },
    handler: function () {
      // UX only - the real confirmation comes from the webhook, not this
      // callback. Just route the user to an order-status page and poll.
      window.location.href = `/order-confirmation/${payment.vstitch_order_id}`;
    },
    modal: {
      ondismiss: function () {
        // User closed the checkout without paying. Our order is still sitting
        // at payment_pending - either they retry, or it's simply abandoned
        // (no restock happens automatically for an abandoned/dismissed
        // checkout, only for an explicit payment.failed from Razorpay - flag
        // this to backend if you want an auto-expiry policy added later).
        window.location.href = `/checkout?retry=${payment.vstitch_order_id}`;
      },
    },
  };

  const razorpayCheckout = new Razorpay(options);
  razorpayCheckout.open();
}
```

### Confirming the outcome on your order-confirmation page

Poll `GET /orders` (documented in `docs/api-orders-products-categories.md`) and read the `order_status` for `vstitch_order_id`:

| `order_status` | Meaning |
|---|---|
| `payment_pending` | Still waiting on the webhook - show a spinner, poll again in ~1–2s |
| `placed` | Payment captured - show success, this now behaves exactly like a normal order |
| `payment_failed` | Payment failed - show a retry option; stock has already been restored, so a retry is a fresh `POST /payments/orders` call |

In the vast majority of cases the webhook lands within a second or two of Checkout's own `handler` firing, so a short poll loop (e.g. every 1.5s, give up after ~20s with a "still processing" message) is enough — don't block the UI waiting synchronously.

---

## POST /payments/webhook

You will not call this — it's the URL you gave Razorpay (`.../payments/webhook`). Documented here only so you understand what drives the status your frontend polls for.

Every request is HMAC-SHA256 verified against the raw body using the webhook secret before anything is processed; unsigned/forged requests get a `400` and change nothing. On `payment.captured`, the order moves `payment_pending → placed`. On `payment.failed`, it moves `payment_pending → payment_failed` and the held stock is released back into inventory. Every other event type you've subscribed to (refunds, disputes, settlements, etc.) is logged but doesn't change order status yet.

---

## Notes for integration

- **This is additive, not a replacement.** `POST /orders` (COD) is untouched — a checkout page can offer both "Cash on Delivery" and "Pay Online" as two buttons calling two different endpoints.
- **Don't call `POST /orders` and `POST /payments/orders` for the same basket** — each one independently decrements stock. Pick one based on the user's chosen payment method.
- **Idempotency:** if your frontend retries `POST /payments/orders` after a network timeout without knowing whether the first call succeeded, you'll get two separate `payment_pending` orders, each holding its own stock. Prefer disabling the "Proceed to Pay" button while the request is in flight rather than auto-retrying.
- **Test mode:** the backend is currently configured with Razorpay **test-mode** keys (`rzp_test_...`). Use [Razorpay's test card/UPI details](https://razorpay.com/docs/payments/payments/test-card-upi-details/) to exercise success and failure paths end-to-end before going live.
- **Error shape:** every handled error returns FastAPI's standard `{"detail": "..."}` body, same as the rest of the API.

---

*Generated from `vstitchapi/paymentApi.py`, `vstitchServices/paymentService.py`, `vstitchServices/razorpayClient.py`, and their DTOs — Vstitch Backend.*
