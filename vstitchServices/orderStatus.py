class OrderStatus:
    """Domain values for VStitch_Orders.OrderStatus, scoped to the cash-on-delivery flow.

    Pipeline (happy path):
        PLACED -> CONFIRMED -> PROCESSING -> SHIPPED -> OUT_FOR_DELIVERY -> DELIVERED

    Exit points off the happy path:
        PLACED / CONFIRMED / PROCESSING -> CANCELLED       (called off before it ships)
        OUT_FOR_DELIVERY                -> DELIVERY_FAILED (customer refused COD / unreachable)

    There is no 'paid' status: COD orders collect cash at the DELIVERED step
    rather than upfront, unlike a gateway-paid order.
    """

    PLACED = "placed"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    DELIVERY_FAILED = "delivery_failed"

    PIPELINE = (PLACED, CONFIRMED, PROCESSING, SHIPPED, OUT_FOR_DELIVERY, DELIVERED)
    TERMINAL = (DELIVERED, CANCELLED, DELIVERY_FAILED)

    ALLOWED_TRANSITIONS = {
        PLACED: (CONFIRMED, CANCELLED),
        CONFIRMED: (PROCESSING, CANCELLED),
        PROCESSING: (SHIPPED, CANCELLED),
        SHIPPED: (OUT_FOR_DELIVERY,),
        OUT_FOR_DELIVERY: (DELIVERED, DELIVERY_FAILED),
        DELIVERED: (),
        CANCELLED: (),
        DELIVERY_FAILED: (),
    }
