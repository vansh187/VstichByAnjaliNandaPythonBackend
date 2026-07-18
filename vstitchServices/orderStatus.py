class OrderStatus:
    """Domain values for VStitch_Orders.OrderStatus.

    Pipeline (happy path, shared by both payment methods):
        PLACED -> CONFIRMED -> PROCESSING -> SHIPPED -> OUT_FOR_DELIVERY -> DELIVERED

    Exit points off the happy path:
        PLACED / CONFIRMED / PROCESSING -> CANCELLED       (called off before it ships)
        OUT_FOR_DELIVERY                -> DELIVERY_FAILED (customer refused COD / unreachable)

    A COD order is created directly at PLACED - cash is only collected at the
    DELIVERED step, so there's no separate payment step to wait on.

    A Razorpay order is created at PAYMENT_PENDING instead: the order row and
    its stock decrement already exist (so the items are held while the
    customer is on the payment screen), but nothing has been charged yet.
    PAYMENT_PENDING only ever resolves via the payment webhook:
        PAYMENT_PENDING -> PLACED          (payment.captured - rejoins the pipeline above)
        PAYMENT_PENDING -> PAYMENT_FAILED  (payment.failed - terminal, stock is restored)
    """

    PAYMENT_PENDING = "payment_pending"
    PAYMENT_FAILED = "payment_failed"
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    DELIVERY_FAILED = "delivery_failed"

    PIPELINE = (PLACED, CONFIRMED, PROCESSING, SHIPPED, OUT_FOR_DELIVERY, DELIVERED)
    TERMINAL = (DELIVERED, CANCELLED, DELIVERY_FAILED, PAYMENT_FAILED)

    ALLOWED_TRANSITIONS = {
        PAYMENT_PENDING: (PLACED, PAYMENT_FAILED),
        PAYMENT_FAILED: (),
        PLACED: (CONFIRMED, CANCELLED),
        CONFIRMED: (PROCESSING, CANCELLED),
        PROCESSING: (SHIPPED, CANCELLED),
        SHIPPED: (OUT_FOR_DELIVERY,),
        OUT_FOR_DELIVERY: (DELIVERED, DELIVERY_FAILED),
        DELIVERED: (),
        CANCELLED: (),
        DELIVERY_FAILED: (),
    }
