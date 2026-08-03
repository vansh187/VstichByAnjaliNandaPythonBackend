import logging
import os
from datetime import datetime, timedelta

from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchServices.orderStatus import OrderStatus, old_statuses_that_can_reach
from vstitchServices.shiprocketClient import ShiprocketClient

logger = logging.getLogger(__name__)

# Best-effort mapping from Shiprocket's free-text `current_status` (webhook
# payload) to our own OrderStatus pipeline. Built from Shiprocket's commonly
# documented status strings, not confirmed against this account's actual
# webhook traffic - any status text that doesn't appear here is logged and
# safely ignored (see handle_tracking_webhook) rather than guessed at, so
# real values seen in production can be added here over time.
#
# CANCELLED/RTO-style statuses are deliberately NOT mapped to
# OrderStatus.CANCELLED here: our own cancel flow (ShipmentService.cancel_
# order) restocks variants when it cancels, and blindly restocking off a
# webhook we're not fully certain we've parsed correctly is a worse failure
# mode than just not auto-cancelling. They map to DELIVERY_FAILED instead,
# which is terminal but restock-free.
SHIPROCKET_STATUS_TO_ORDER_STATUS = {
    "PICKUP SCHEDULED": OrderStatus.CONFIRMED,
    "PICKUP GENERATED": OrderStatus.CONFIRMED,
    "PICKUP QUEUED": OrderStatus.CONFIRMED,
    "PICKED UP": OrderStatus.SHIPPED,
    "IN TRANSIT": OrderStatus.SHIPPED,
    "OUT FOR DELIVERY": OrderStatus.OUT_FOR_DELIVERY,
    "DELIVERED": OrderStatus.DELIVERED,
    "UNDELIVERED": OrderStatus.DELIVERY_FAILED,
    "RTO INITIATED": OrderStatus.DELIVERY_FAILED,
    "RTO DELIVERED": OrderStatus.DELIVERY_FAILED,
    "LOST": OrderStatus.DELIVERY_FAILED,
    "DAMAGED": OrderStatus.DELIVERY_FAILED,
    "DISPOSED OFF": OrderStatus.DELIVERY_FAILED,
}


def _dig(data, *keys):
    """Safely walks a chain of dict lookups, returning None the moment
    anything along the way isn't a dict or the key is missing - used to read
    optional fields out of Shiprocket responses without risking an
    AttributeError/KeyError on a response shape that turns out to differ
    slightly from what's documented.
    """
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _coerce_bigint(value):
    """Returns value as an int if it cleanly represents one, else None -
    ShiprocketOrderId is a BIGINT column, and Shiprocket's own "Test Webhook"
    button sends placeholder text (e.g. "dummpy shiprocket order id 123") in
    that field, which must never reach the query as-is or Postgres raises
    InvalidTextRepresentation.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


# Caps how much of a Shiprocket error body can end up in a raised ValueError -
# that message flows into both application logs and, via the ops API's
# `except ValueError -> HTTPException(409, detail=str(...))`, an HTTP
# response body, so an unbounded raw response dict (Shiprocket's fallback
# when there's no top-level "message") must never be embedded whole.
MAX_SHIPROCKET_ERROR_MESSAGE_LENGTH = 300

# VStitch_Orders.PaymentMethod values -> Shiprocket's own payment_method
# strings ("COD" collects cash on delivery from the customer; "Prepaid" is
# used for the already-paid-at-the-gateway Razorpay path).
SHIPROCKET_PAYMENT_METHOD_BY_ORDER_PAYMENT_METHOD = {
    "cod": "COD",
    "razorpay": "Prepaid",
}

# A customer can only ask to cancel while we haven't yet handed the parcel to
# a courier for real - matches OrderStatus.ALLOWED_TRANSITIONS' own CANCELLED
# exits (SHIPPED onward has no CANCELLED transition at all).
CANCELLABLE_ORDER_STATUSES = (OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PROCESSING)

# A customer can request a return/replace once an order has been delivered
# for at least this many days - no upper bound is enforced (only this floor).
RETURN_REPLACE_ELIGIBILITY_DAYS = 7

# VStitch_ReturnOrderItems.IssueCategory CHECK-constraint values (migration
# 0010) - mirrored in vstitchDTO/shipmentRequestDTO.py's
# VALID_REPLACE_ISSUE_CATEGORIES, which is what actually validates the
# incoming request; this copy is what create_replace itself trusts.
REPLACE_ISSUE_CATEGORIES = ("size_issue", "defect")


class ShipmentService:
    """Builds Shiprocket requests from VStitch order data and drives the
    shipment lifecycle (create, track, cancel, return) - the only place order
    data is translated into Shiprocket's request shapes. ShiprocketClient
    itself now caches its auth token process-wide (see its docstring), so
    every method here just calls it directly rather than pairing a login/
    logout around each request.
    """

    def __init__(self):
        pickup_location = os.getenv("SHIPROCKET_PICKUP_LOCATION")
        if not pickup_location:
            raise ValueError("SHIPROCKET_PICKUP_LOCATION is not configured in the environment.")
        self.pickup_location = pickup_location
        # Only required for courier-serviceability checks (Shiprocket needs a
        # numeric pincode there, not the location name) - not every caller of
        # this service needs it, so it's read but not validated in __init__.
        self.pickup_postcode = os.getenv("SHIPROCKET_PICKUP_POSTCODE")
        self.order_persistence = OrderPersistence()
        self.shiprocket_client = ShiprocketClient()

    # --- Order creation (triggered right after order placement: immediately
    # for COD, on Razorpay payment capture for gateway orders) -------------

    def create_shipment_for_order(self, vstitch_order_id):
        """Fetches the order, validates every item has the data Shiprocket
        requires, creates the shipment, then persists Shiprocket's own
        order_id/shipment_id onto VStitch_Orders - every fulfillment/
        tracking/cancel call after this one is keyed by those, not by our own
        order id. Raises ValueError - never a raw exception - on any
        problem, so a single except clause at the call site catches
        everything this can throw.
        """
        order = self.order_persistence.get_order_for_shipment(vstitch_order_id)
        if order is None:
            raise ValueError(f"VStitch order {vstitch_order_id} was not found - cannot create a shipment for it.")
        if not order["items"]:
            raise ValueError(f"VStitch order {vstitch_order_id} has no line items - cannot create a shipment for it.")

        payload = self._build_shiprocket_payload(order)
        response = self.shiprocket_client.create_order(payload)

        shiprocket_shipment_id = response.get("shipment_id")
        self.order_persistence.save_shiprocket_shipment_ids(
            vstitch_order_id, response.get("order_id"), shiprocket_shipment_id, "shiprocket-integration"
        )

        # Auto-assign AWB/courier right away, best-effort: the shipment above
        # is already created and persisted, so a failure here (Shiprocket
        # hiccup, no serviceable courier yet, etc.) must not be reported as
        # shipment creation itself failing - it's caught and logged here, not
        # re-raised, leaving assign_awb_for_order's ops endpoint as the
        # manual recovery path for the rare case this doesn't succeed inline.
        if shiprocket_shipment_id:
            try:
                self._assign_awb(vstitch_order_id, shiprocket_shipment_id)
            except Exception:
                logger.exception(
                    "Shiprocket AWB assignment failed for VStitch order %s - shipment was created (Shiprocket "
                    "order/shipment ids saved), but no courier/AWB is assigned yet - assign one manually via "
                    "POST /ops/shipments/%s/awb.",
                    vstitch_order_id,
                    vstitch_order_id,
                )

        return response

    def _build_shiprocket_payload(self, order):
        total_weight_kg = 0
        max_length_cm = 0
        max_breadth_cm = 0
        max_height_cm = 0
        order_items_payload = []

        for item in order["items"]:
            missing_fields = [
                field_name
                for field_name in ("sku", "weight_kg", "length_cm", "breadth_cm", "height_cm")
                if item.get(field_name) is None
            ]
            if missing_fields:
                raise ValueError(
                    f"Order item '{item['product_name']}' (order {order['vstitch_order_id']}) is missing "
                    f"{', '.join(missing_fields)} - add these to its product variant before shipping."
                )

            total_weight_kg += float(item["weight_kg"]) * item["quantity"]
            max_length_cm = max(max_length_cm, float(item["length_cm"]))
            max_breadth_cm = max(max_breadth_cm, float(item["breadth_cm"]))
            max_height_cm = max(max_height_cm, float(item["height_cm"]))

            order_items_payload.append(
                {
                    "name": item["product_name"],
                    "sku": item["sku"],
                    "units": item["quantity"],
                    "selling_price": float(item["unit_price"]),
                }
            )

        billing_first_name, _, billing_last_name = order["shipping_recipient_name"].partition(" ")

        return {
            "order_id": str(order["vstitch_order_id"]),
            "order_date": order["created_date"].strftime("%Y-%m-%d %H:%M"),
            "pickup_location": self.pickup_location,
            "billing_customer_name": billing_first_name,
            "billing_last_name": billing_last_name,
            "billing_address": order["shipping_address_line1"],
            "billing_address_2": order["shipping_address_line2"] or "",
            "billing_city": order["shipping_city"],
            "billing_pincode": order["shipping_postal_code"],
            "billing_state": order["shipping_state"],
            "billing_country": order["shipping_country"],
            "billing_email": order["email"],
            "billing_phone": order["shipping_phone_number"],
            "shipping_is_billing": True,
            "order_items": order_items_payload,
            "payment_method": SHIPROCKET_PAYMENT_METHOD_BY_ORDER_PAYMENT_METHOD[order["payment_method"]],
            "sub_total": float(order["total_amount"]),
            # A single box is assumed for the whole order (max footprint across
            # items, summed weight) since Shiprocket's adhoc-order API takes one
            # set of dimensions per shipment, not per item - true multi-box
            # packing would need the separate multi-piece shipment API.
            "length": max_length_cm,
            "breadth": max_breadth_cm,
            "height": max_height_cm,
            "weight": round(total_weight_kg, 3),
        }

    # --- Pre-order (checkout page) ----------------------------------------

    def check_serviceability(self, delivery_postcode, weight_kg, cash_on_delivery):
        """Delivery ETA / COD availability / shipping charge for the
        checkout page, before payment. Raises ValueError if
        SHIPROCKET_PICKUP_POSTCODE isn't configured - this call needs a
        numeric pincode, unlike order creation which only needs the pickup
        location's name.
        """
        if not self.pickup_postcode:
            raise ValueError("SHIPROCKET_PICKUP_POSTCODE is not configured in the environment.")
        return self.shiprocket_client.check_serviceability(
            self.pickup_postcode, delivery_postcode, weight_kg, cash_on_delivery
        )

    # --- Tracking / cancellation (customer-facing) ------------------------

    def get_tracking_for_order(self, vstitch_order_id, vstitch_user_id):
        """Returns live Shiprocket tracking for one order, scoped to the
        requesting user - raises ValueError (not found/not yours/not shipped
        yet) rather than ever looking up another user's order.
        """
        order = self._get_owned_order_for_tracking(vstitch_order_id, vstitch_user_id)
        if order["shiprocket_order_id"] is None:
            raise ValueError(f"Order {vstitch_order_id} has not shipped yet - nothing to track.")
        return self.shiprocket_client.track_order(order["shiprocket_order_id"])

    def cancel_order(self, vstitch_order_id, vstitch_user_id):
        """Cancels an order pre-dispatch. Cancels on the Shiprocket side
        first (if a shipment already exists there) - only if that succeeds
        (or there was never a Shiprocket shipment to begin with) does the
        VStitch order itself get marked cancelled and its stock restored,
        so a Shiprocket rejection (already picked up, in transit) never
        leaves our own order state out of sync with what's actually shipping.
        """
        order = self._get_owned_order_for_tracking(vstitch_order_id, vstitch_user_id)
        if order["order_status"] not in CANCELLABLE_ORDER_STATUSES:
            raise ValueError(
                f"Order {vstitch_order_id} is '{order['order_status']}' and can no longer be cancelled."
            )

        if order["shiprocket_order_id"] is not None:
            self.shiprocket_client.cancel_orders([order["shiprocket_order_id"]])

        was_cancelled = self.order_persistence.cancel_order_with_restock(
            vstitch_order_id, "customer-cancel", CANCELLABLE_ORDER_STATUSES
        )
        if not was_cancelled:
            raise ValueError(f"Order {vstitch_order_id} could not be cancelled - it may have just changed status.")

    def _get_owned_order_for_tracking(self, vstitch_order_id, vstitch_user_id):
        order = self.order_persistence.get_order_for_tracking(vstitch_order_id)
        # Same "not found" message for a missing order and one owned by
        # someone else - confirming an order id exists but belongs to another
        # user is exactly the account-enumeration leak this guards against.
        if order is None or order["vstitch_user_id"] != vstitch_user_id:
            raise ValueError(f"Order {vstitch_order_id} was not found.")
        return order

    # --- Returns / Replace ---------------------------------------------------

    def create_return(self, vstitch_order_id, vstitch_user_id, reason):
        """Records a return request and files it with Shiprocket. Only valid
        once an order has actually been delivered for at least
        RETURN_REPLACE_ELIGIBILITY_DAYS, and only if no other return/replace
        request is already open against this order. The exact
        /orders/create/return request shape wasn't provided when this was
        built, so it's modeled on Shiprocket's adhoc create-order shape with
        pickup/delivery swapped (their documented pattern for a return);
        verify against Shiprocket's return API reference before relying on
        this in production. Known limitation, left as-is: the destination
        ("shipping_address") is only a location-name string with no city/
        state/pincode override - see _swap_to_return_pickup_shape.
        """
        order = self._get_owned_order_for_tracking(vstitch_order_id, vstitch_user_id)
        if order["order_status"] != OrderStatus.DELIVERED:
            raise ValueError(f"Order {vstitch_order_id} has not been delivered yet - nothing to return.")
        self._assert_return_replace_eligible(order, vstitch_order_id)
        self._assert_no_open_return_request(vstitch_order_id)

        full_order = self.order_persistence.get_order_for_shipment(vstitch_order_id)
        if full_order is None:
            raise ValueError(f"Order {vstitch_order_id} was not found.")

        # Claims the "one open request per order" slot atomically (backed by
        # uq_return_orders_open_per_order) BEFORE calling Shiprocket - not
        # after - so a duplicate concurrent request is blocked by the DB
        # before a second real Shiprocket shipment is ever filed. See
        # _assert_no_open_return_request's docstring for why that earlier
        # check alone isn't sufficient (TOCTOU).
        vstitch_return_order_id = self.order_persistence.create_return_order_claim(
            vstitch_order_id, "return", reason, "customer-return-request"
        )

        return_payload = self._build_shiprocket_payload(full_order)
        return_payload["order_id"] = f"{vstitch_order_id}-RETURN-{os.urandom(4).hex()}"
        self._swap_to_return_pickup_shape(return_payload)

        try:
            response = self.shiprocket_client.create_return_order(return_payload)
        except Exception:
            self._cancel_return_claim_best_effort(vstitch_return_order_id)
            raise

        self.order_persistence.save_return_order_shiprocket_ids(
            vstitch_return_order_id, response.get("order_id"), response.get("shipment_id"), "shiprocket-integration"
        )
        return vstitch_return_order_id, response

    def create_replace(self, vstitch_order_id, vstitch_user_id, issue_category, reason, items):
        """Records a replace request (size/defect issue on specific order
        items) and files the same kind of Shiprocket return-pickup shipment
        create_return does, scoped to only the requested items. `items` is a
        list of {"vstitch_order_item_id", "quantity"} dicts (already
        Pydantic-validated for shape/bounds by CreateReplaceRequestDTO).
        Shipping the replacement item back out is a manual ops step, not
        automated here.
        """
        if issue_category not in REPLACE_ISSUE_CATEGORIES:
            raise ValueError(f"issue_category must be one of {REPLACE_ISSUE_CATEGORIES}.")

        order = self._get_owned_order_for_tracking(vstitch_order_id, vstitch_user_id)
        if order["order_status"] != OrderStatus.DELIVERED:
            raise ValueError(f"Order {vstitch_order_id} has not been delivered yet - nothing to replace.")
        self._assert_return_replace_eligible(order, vstitch_order_id)
        self._assert_no_open_return_request(vstitch_order_id)

        # Merge repeated entries for the same order item into one running
        # total before checking against what was actually ordered - two
        # separate {item_id: 42, quantity: 1} entries for an item that was
        # only ordered once must jointly fail the quantity check, not each
        # pass it individually against the same un-decremented total.
        requested_quantity_by_item_id = {}
        for item in items:
            item_id = item["vstitch_order_item_id"]
            requested_quantity_by_item_id[item_id] = requested_quantity_by_item_id.get(item_id, 0) + item["quantity"]

        owned_items_by_id = self.order_persistence.get_order_items_by_ids_for_order(
            vstitch_order_id, list(requested_quantity_by_item_id.keys())
        )
        for item_id, total_quantity in requested_quantity_by_item_id.items():
            owned_item = owned_items_by_id.get(item_id)
            # Same "not found" message whether the item id doesn't exist at
            # all or belongs to a different order - confirming an item id
            # exists but belongs to someone else's order is exactly the
            # enumeration leak _get_owned_order_for_tracking already guards
            # against at the order level.
            if owned_item is None:
                raise ValueError(f"Order {vstitch_order_id} was not found.")
            if total_quantity > owned_item["quantity"]:
                raise ValueError(
                    f"Requested quantity for order item {item_id} exceeds the "
                    f"{owned_item['quantity']} originally ordered."
                )

        full_order = self.order_persistence.get_order_for_shipment(vstitch_order_id)
        if full_order is None:
            raise ValueError(f"Order {vstitch_order_id} was not found.")

        requested_item_id_set = set(requested_quantity_by_item_id.keys())
        filtered_items = [
            item for item in full_order["items"] if item["vstitch_order_item_id"] in requested_item_id_set
        ]
        if not filtered_items:
            raise ValueError(f"Order {vstitch_order_id} was not found.")
        filtered_order = dict(full_order, items=filtered_items)

        item_rows = [
            {"vstitch_order_item_id": item_id, "quantity": total_quantity, "issue_category": issue_category}
            for item_id, total_quantity in requested_quantity_by_item_id.items()
        ]

        # Same claim-before-Shiprocket-call shape as create_return - see its
        # comment for why the slot is claimed here, not after the Shiprocket
        # call succeeds.
        vstitch_return_order_id = self.order_persistence.create_replace_request_claim(
            vstitch_order_id, f"[{issue_category}] {reason}", item_rows, "customer-replace-request"
        )

        replace_payload = self._build_shiprocket_payload(filtered_order)
        replace_payload["order_id"] = f"{vstitch_order_id}-REPLACE-{os.urandom(4).hex()}"
        self._swap_to_return_pickup_shape(replace_payload)

        try:
            response = self.shiprocket_client.create_return_order(replace_payload)
        except Exception:
            self._cancel_return_claim_best_effort(vstitch_return_order_id)
            raise

        self.order_persistence.save_return_order_shiprocket_ids(
            vstitch_return_order_id, response.get("order_id"), response.get("shipment_id"), "shiprocket-integration"
        )
        return vstitch_return_order_id, response

    def _cancel_return_claim_best_effort(self, vstitch_return_order_id):
        """Frees a just-claimed return/replace slot after its Shiprocket
        call failed, so the order isn't left permanently blocked by a
        failed attempt. Never raises: this runs inside an except block
        that's about to re-raise the real (Shiprocket) failure, and a
        problem freeing the claim must not replace or mask that error -
        it's logged instead, leaving a stuck 'requested' row as the only
        symptom for ops to clean up manually in the rare case this itself
        fails.
        """
        try:
            self.order_persistence.cancel_return_order_claim(vstitch_return_order_id, "shiprocket-integration")
        except Exception:
            logger.exception(
                "Failed to release return/replace claim %s after its Shiprocket call failed - it will "
                "remain 'requested' and block new requests for its order until cleaned up manually.",
                vstitch_return_order_id,
            )

    def _assert_return_replace_eligible(self, order, vstitch_order_id):
        """Raises ValueError unless the order has been delivered for at
        least RETURN_REPLACE_ELIGIBILITY_DAYS. Always reads delivered_date
        fresh off the order dict just fetched from the DB (get_order_for_
        tracking) - never a client-supplied value or a stale value cached
        from an earlier GET /orders response."""
        delivered_date = order.get("delivered_date")
        if delivered_date is None:
            raise ValueError(f"Order {vstitch_order_id} has no recorded delivery date yet - nothing to return.")
        eligible_from = delivered_date + timedelta(days=RETURN_REPLACE_ELIGIBILITY_DAYS)
        # datetime.utcnow() (naive), not datetime.now(timezone.utc) (aware):
        # DeliveredDate is a plain TIMESTAMP (no time zone) column, so
        # psycopg2 returns delivered_date as a naive datetime already in
        # server-UTC terms - comparing it against an aware datetime would
        # raise TypeError, not just be wrong.
        if datetime.utcnow() < eligible_from:
            raise ValueError(
                f"Order {vstitch_order_id} becomes eligible for return/replace on "
                f"{eligible_from.strftime('%Y-%m-%d')} ({RETURN_REPLACE_ELIGIBILITY_DAYS} days after delivery)."
            )

    def _assert_no_open_return_request(self, vstitch_order_id):
        """Raises ValueError if a return/replace request is already open
        against this order - prevents a duplicate Shiprocket return-pickup
        shipment from being filed by a double-click or resubmission."""
        open_request = self.order_persistence.find_open_return_request_for_order(vstitch_order_id)
        if open_request is not None:
            raise ValueError(
                f"Order {vstitch_order_id} already has a {open_request['request_type']} request "
                f"(status: {open_request['status']}) in progress."
            )

    def _swap_to_return_pickup_shape(self, payload):
        """Mutates a Shiprocket adhoc-order-shape payload in place, swapping
        pickup/delivery so the customer's address becomes the pickup point
        and our own pickup location becomes the delivery destination - the
        shape both create_return and create_replace file with Shiprocket.
        Known limitation, left as-is: shipping_address is only a location-
        name string with no city/state/pincode override for the warehouse
        destination.
        """
        payload["pickup_customer_name"] = payload.pop("billing_customer_name")
        payload["pickup_last_name"] = payload.pop("billing_last_name")
        payload["pickup_address"] = payload.pop("billing_address")
        payload["pickup_city"] = payload.pop("billing_city")
        payload["pickup_pincode"] = payload.pop("billing_pincode")
        payload["pickup_state"] = payload.pop("billing_state")
        payload["pickup_country"] = payload.pop("billing_country")
        payload["pickup_email"] = payload.pop("billing_email")
        payload["pickup_phone"] = payload.pop("billing_phone")
        payload["shipping_customer_name"] = "VStitch Warehouse"
        payload["shipping_address"] = self.pickup_location
        payload.pop("shipping_is_billing", None)
        payload.pop("billing_address_2", None)
        return payload

    # --- Fulfillment / ops (internal, not customer-facing) -----------------

    def assign_awb_for_order(self, vstitch_order_id):
        """Assigns a courier/AWB to an already-created shipment and persists
        the result onto VStitch_Orders. Raises ValueError if the order has no
        Shiprocket shipment yet (create_shipment_for_order hasn't run/
        succeeded for it) - there's nothing to assign a courier to - or if
        one is already assigned, so a redundant/unaware manual call can never
        silently overwrite a valid courier with a different one. This is
        also the manual recovery path for an order whose shipment was
        created but whose automatic AWB assignment (see
        create_shipment_for_order) didn't succeed inline.
        """
        order = self.order_persistence.get_order_for_tracking(vstitch_order_id)
        if order is None:
            raise ValueError(f"Order {vstitch_order_id} was not found.")
        if order["shiprocket_shipment_id"] is None:
            raise ValueError(f"Order {vstitch_order_id} has no Shiprocket shipment yet - create it first.")
        if order["awb_code"] is not None:
            raise ValueError(
                f"Order {vstitch_order_id} already has AWB {order['awb_code']} assigned - not re-assigning."
            )

        return self._assign_awb(vstitch_order_id, order["shiprocket_shipment_id"])

    def _assign_awb(self, vstitch_order_id, shiprocket_shipment_id):
        """Shared by assign_awb_for_order (manual, ops-triggered) and
        create_shipment_for_order (automatic, right after shipment
        creation) - Shiprocket auto-picks the courier since assign_awb takes
        no preferred-courier parameter. Raises ValueError if the response
        has no awb_code, rather than treating that as a silent no-op - a
        200-with-no-courier-serviceable response (Shiprocket embeds
        rejections in a 200 body, the same pattern its create-order endpoint
        uses) must surface as a failure to the caller, since neither
        create_shipment_for_order's log-and-continue nor an ops caller
        checking the return value can catch a failure that raises nothing.
        """
        response = self.shiprocket_client.assign_awb(shiprocket_shipment_id)
        awb_code = _dig(response, "response", "data", "awb_code")
        courier_name = _dig(response, "response", "data", "courier_name")
        if not awb_code:
            error_message = _dig(response, "message") or str(response)
            if len(error_message) > MAX_SHIPROCKET_ERROR_MESSAGE_LENGTH:
                error_message = error_message[:MAX_SHIPROCKET_ERROR_MESSAGE_LENGTH] + "...(truncated)"
            raise ValueError(f"Shiprocket did not assign an AWB for shipment {shiprocket_shipment_id}: {error_message}")

        # Guarded write, not the plain save_awb_details the tracking webhook
        # uses: the assign_awb_for_order pre-check above (or "no AWB yet" in
        # create_shipment_for_order) only rules out an *already-known*
        # AwbCode - it can't see a concurrent assignment that's still
        # in-flight. This UPDATE is the actual point of atomicity: only the
        # first caller to commit it persists, closing that window.
        was_assigned = self.order_persistence.save_awb_details_if_unset(
            vstitch_order_id, awb_code, courier_name, "shiprocket-ops"
        )
        if not was_assigned:
            raise ValueError(
                f"Order {vstitch_order_id} already had an AWB assigned by the time Shiprocket responded to this "
                f"request (courier {courier_name}, AWB {awb_code}) - lost the race to a concurrent assignment, "
                f"so this one was not persisted."
            )
        return response

    def _resolve_shipment_ids(self, vstitch_order_ids):
        """Looks up each order's Shiprocket shipment id, raising ValueError
        naming any order that doesn't have one yet - pickup/label/manifest
        generation all operate on shipment ids and silently skipping an
        unresolvable order would hide a real gap in the batch.
        """
        shipment_ids = []
        for vstitch_order_id in vstitch_order_ids:
            order = self.order_persistence.get_order_for_tracking(vstitch_order_id)
            if order is None or order["shiprocket_shipment_id"] is None:
                raise ValueError(f"Order {vstitch_order_id} has no Shiprocket shipment yet - create it first.")
            shipment_ids.append(order["shiprocket_shipment_id"])
        return shipment_ids

    def generate_pickup_for_orders(self, vstitch_order_ids):
        return self.shiprocket_client.generate_pickup(self._resolve_shipment_ids(vstitch_order_ids))

    def generate_label_for_orders(self, vstitch_order_ids):
        return self.shiprocket_client.generate_label(self._resolve_shipment_ids(vstitch_order_ids))

    def generate_manifest_for_orders(self, vstitch_order_ids):
        return self.shiprocket_client.generate_manifest(self._resolve_shipment_ids(vstitch_order_ids))

    def generate_invoice_for_orders(self, vstitch_order_ids):
        """Invoice generation is keyed by Shiprocket's order id, not its
        shipment id - the one Shiprocket call in this file that isn't."""
        shiprocket_order_ids = []
        for vstitch_order_id in vstitch_order_ids:
            order = self.order_persistence.get_order_for_tracking(vstitch_order_id)
            if order is None or order["shiprocket_order_id"] is None:
                raise ValueError(f"Order {vstitch_order_id} has no Shiprocket order yet - create it first.")
            shiprocket_order_ids.append(order["shiprocket_order_id"])
        return self.shiprocket_client.generate_invoice(shiprocket_order_ids)

    def get_ndr_orders(self):
        return self.shiprocket_client.get_ndr_orders()

    def take_ndr_action(self, ndr_action_payload):
        return self.shiprocket_client.take_ndr_action(ndr_action_payload)

    def sync_order_status_from_shiprocket(self, vstitch_order_id):
        """Admin-triggered reconciliation for when the tracking webhook never
        fired for an order (not yet configured, missed delivery, timing gap)
        and VStitch_Orders.OrderStatus has drifted from Shiprocket's actual
        status. Pulls the live status by AWB (see ShiprocketClient.
        track_by_awb) and applies it through the exact same status map and
        guarded update handle_tracking_webhook uses, so this can never push
        an invalid/backwards transition either. Raises ValueError (-> 409 at
        the API layer) if the order doesn't exist or has no AWB assigned yet
        - there's nothing to reconcile against in that case.
        """
        order = self.order_persistence.get_order_for_tracking(vstitch_order_id)
        if order is None:
            raise ValueError(f"Order {vstitch_order_id} was not found.")
        if order["awb_code"] is None:
            raise ValueError(f"Order {vstitch_order_id} has no AWB assigned yet - nothing to sync against.")

        response = self.shiprocket_client.track_by_awb(order["awb_code"])
        shipment_track = _dig(response, "tracking_data", "shipment_track")
        current_status_text = ""
        if isinstance(shipment_track, list) and shipment_track:
            # _dig, not shipment_track[-1].get(...): the last entry isn't
            # guaranteed to be a dict if Shiprocket's response shape ever
            # deviates from what's documented (same defensive stance _dig
            # exists for elsewhere in this file) - a bare .get() here would
            # raise AttributeError on a malformed entry instead of just
            # falling through to the "unmapped status" no-op below.
            current_status_text = (_dig(shipment_track[-1], "current_status") or "").strip().upper()

        old_status = order["order_status"]
        new_order_status = SHIPROCKET_STATUS_TO_ORDER_STATUS.get(current_status_text)
        if new_order_status is None or new_order_status == old_status:
            return {"vstitch_order_id": vstitch_order_id, "old_status": old_status, "new_status": old_status, "updated": False}

        old_statuses = old_statuses_that_can_reach(new_order_status)
        was_updated = bool(old_statuses) and self.order_persistence.update_order_status(
            vstitch_order_id, new_order_status, old_statuses, "shiprocket-sync"
        )
        return {
            "vstitch_order_id": vstitch_order_id,
            "old_status": old_status,
            "new_status": new_order_status if was_updated else old_status,
            "updated": was_updated,
        }

    # --- Inbound tracking webhook --------------------------------------

    def handle_tracking_webhook(self, payload):
        """Applies one Shiprocket tracking-event delivery: updates AWB/
        courier if present, then advances OrderStatus if the reported status
        maps to a known value and is actually a valid forward transition
        from wherever the order currently is. Every exit path is a no-op,
        never a raise - an unrecognized order, an unmapped status string, or
        an out-of-order/duplicate delivery are all expected occurrences for
        a webhook, not bugs, so none of them should turn into a 500 that
        makes Shiprocket retry a delivery that will never resolve.
        """
        shiprocket_order_id = _coerce_bigint(_dig(payload, "order_id")) or _coerce_bigint(_dig(payload, "sr_order_id"))
        if not shiprocket_order_id:
            # Logs the payload's top-level field names only, never the full
            # payload - Shiprocket's webhook body carries customer PII
            # (shipping address, phone) even on this "couldn't identify the
            # order" path, and that's not something an application log
            # should ever hold.
            payload_keys = list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
            logger.info(
                "Shiprocket tracking webhook had no numeric order_id/sr_order_id - ignoring. Payload fields: %s",
                payload_keys,
            )
            return

        order = self.order_persistence.find_order_by_shiprocket_order_id(shiprocket_order_id)
        if order is None:
            logger.info("Shiprocket tracking webhook for unknown order_id %s - ignoring.", shiprocket_order_id)
            return

        awb_code = _dig(payload, "awb") or _dig(payload, "awb_code")
        courier_name = _dig(payload, "courier_name")
        if awb_code:
            self.order_persistence.save_awb_details(
                order["vstitch_order_id"], awb_code, courier_name, "shiprocket-webhook"
            )

        current_status_text = (_dig(payload, "current_status") or "").strip().upper()
        new_order_status = SHIPROCKET_STATUS_TO_ORDER_STATUS.get(current_status_text)
        if new_order_status is None:
            logger.info(
                "Shiprocket tracking webhook for order %s has unmapped status '%s' - ignoring. Add it to "
                "SHIPROCKET_STATUS_TO_ORDER_STATUS once confirmed.",
                order["vstitch_order_id"],
                current_status_text,
            )
            return

        old_statuses = old_statuses_that_can_reach(new_order_status)
        if not old_statuses:
            return
        was_updated = self.order_persistence.update_order_status(
            order["vstitch_order_id"], new_order_status, old_statuses, "shiprocket-webhook"
        )
        if not was_updated:
            logger.info(
                "Shiprocket tracking webhook for order %s reported '%s' but the order's current status "
                "doesn't allow that transition (stale/out-of-order delivery) - ignored.",
                order["vstitch_order_id"],
                current_status_text,
            )
