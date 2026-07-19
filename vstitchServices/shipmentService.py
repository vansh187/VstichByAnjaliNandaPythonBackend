import logging
import os

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

# Razorpay orders are always prepaid at the gateway before this service is
# ever invoked (see PaymentService.handle_webhook_event) - COD orders never
# reach Shiprocket order creation through this path, so there's no COD
# branch to map here.
SHIPROCKET_PAYMENT_METHOD = "Prepaid"

# A customer can only ask to cancel while we haven't yet handed the parcel to
# a courier for real - matches OrderStatus.ALLOWED_TRANSITIONS' own CANCELLED
# exits (SHIPPED onward has no CANCELLED transition at all).
CANCELLABLE_ORDER_STATUSES = (OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PROCESSING)


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

    # --- Order creation (triggered by payment capture) -------------------

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

        self.order_persistence.save_shiprocket_shipment_ids(
            vstitch_order_id, response.get("order_id"), response.get("shipment_id"), "shiprocket-integration"
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
            "payment_method": SHIPROCKET_PAYMENT_METHOD,
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

    # --- Returns -----------------------------------------------------------

    def create_return(self, vstitch_order_id, vstitch_user_id, reason):
        """Records a return request and files it with Shiprocket. Only valid
        once an order has actually been delivered - there's nothing to
        return before then. The exact /orders/create/return request shape
        wasn't provided when this was built, so it's modeled on Shiprocket's
        adhoc create-order shape with pickup/delivery swapped (their
        documented pattern for a return); verify against Shiprocket's return
        API reference before relying on this in production.
        """
        order = self._get_owned_order_for_tracking(vstitch_order_id, vstitch_user_id)
        if order["order_status"] != OrderStatus.DELIVERED:
            raise ValueError(f"Order {vstitch_order_id} has not been delivered yet - nothing to return.")

        full_order = self.order_persistence.get_order_for_shipment(vstitch_order_id)
        if full_order is None:
            raise ValueError(f"Order {vstitch_order_id} was not found.")

        return_payload = self._build_shiprocket_payload(full_order)
        return_payload["order_id"] = f"{vstitch_order_id}-RETURN-{os.urandom(4).hex()}"
        # Swap pickup/delivery: the customer's address becomes the pickup
        # point, our own pickup location becomes the delivery destination.
        return_payload["pickup_customer_name"] = return_payload.pop("billing_customer_name")
        return_payload["pickup_last_name"] = return_payload.pop("billing_last_name")
        return_payload["pickup_address"] = return_payload.pop("billing_address")
        return_payload["pickup_city"] = return_payload.pop("billing_city")
        return_payload["pickup_pincode"] = return_payload.pop("billing_pincode")
        return_payload["pickup_state"] = return_payload.pop("billing_state")
        return_payload["pickup_country"] = return_payload.pop("billing_country")
        return_payload["pickup_email"] = return_payload.pop("billing_email")
        return_payload["pickup_phone"] = return_payload.pop("billing_phone")
        return_payload["shipping_customer_name"] = "VStitch Warehouse"
        return_payload["shipping_address"] = self.pickup_location
        return_payload.pop("shipping_is_billing", None)
        return_payload.pop("billing_address_2", None)

        response = self.shiprocket_client.create_return_order(return_payload)

        vstitch_return_order_id = self.order_persistence.create_return_order(
            vstitch_order_id,
            reason,
            "customer-return-request",
            shiprocket_return_order_id=response.get("order_id"),
            shiprocket_shipment_id=response.get("shipment_id"),
        )
        return vstitch_return_order_id, response

    # --- Fulfillment / ops (internal, not customer-facing) -----------------

    def assign_awb_for_order(self, vstitch_order_id):
        """Assigns a courier/AWB to an already-created shipment and persists
        the result onto VStitch_Orders. Raises ValueError if the order has no
        Shiprocket shipment yet (create_shipment_for_order hasn't run/
        succeeded for it) - there's nothing to assign a courier to.
        """
        order = self.order_persistence.get_order_for_tracking(vstitch_order_id)
        if order is None:
            raise ValueError(f"Order {vstitch_order_id} was not found.")
        if order["shiprocket_shipment_id"] is None:
            raise ValueError(f"Order {vstitch_order_id} has no Shiprocket shipment yet - create it first.")

        response = self.shiprocket_client.assign_awb(order["shiprocket_shipment_id"])
        awb_code = _dig(response, "response", "data", "awb_code")
        courier_name = _dig(response, "response", "data", "courier_name")
        if awb_code:
            self.order_persistence.save_awb_details(vstitch_order_id, awb_code, courier_name, "shiprocket-ops")
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
        shiprocket_order_id = _dig(payload, "order_id") or _dig(payload, "sr_order_id")
        if not shiprocket_order_id:
            logger.info("Shiprocket tracking webhook had no order_id/sr_order_id - ignoring. Payload: %s", payload)
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
