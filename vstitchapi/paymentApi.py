from fastapi import APIRouter, Depends, HTTPException, Request

from vstitchDTO.createOrderRequestDTO import CreateOrderRequestDTO
from vstitchDTO.paymentResponseDTO import CreatePaymentOrderResponseDTO
from vstitchServices.authDependency import get_current_user
from vstitchServices.paymentService import PaymentService


class PaymentApi:
    """Exposes the Razorpay checkout endpoints: creating a gateway order for
    the authenticated user, and the public webhook Razorpay calls back on.
    """

    def __init__(self):
        self.payment_service = PaymentService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/payments/orders",
            self.create_payment_order,
            methods=["POST"],
            response_model=CreatePaymentOrderResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/payments/webhook",
            self.razorpay_webhook,
            methods=["POST"],
        )

    # Sync def for the same reason as OrderApi.create_order - psycopg2 blocks,
    # and FastAPI's worker-thread dispatch is what gives real concurrency here.
    def create_payment_order(
        self,
        create_order_request_dto: CreateOrderRequestDTO,
        request: Request,
        current_user: dict = Depends(get_current_user),
    ):
        client_ip_address = request.client.host if request.client else "unknown"
        try:
            return self.payment_service.create_payment_order(
                create_order_request_dto, current_user["vstitch_user_id"], client_ip_address
            )
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Something went wrong while starting your payment. Please try again.",
            )

    # Deliberately async here, unlike the rest of the API: Razorpay signs the
    # webhook over the exact raw request bytes, and Starlette only exposes
    # those via the async `request.body()` - there is no synchronous path to
    # the unparsed body. The DB work this triggers is a handful of short,
    # indexed statements on a route Razorpay calls far less often than a
    # shopper browses the catalog, so briefly blocking the event loop here is
    # an accepted, deliberate trade-off rather than an oversight.
    #
    # No auth dependency: Razorpay calls this directly with no bearer token.
    # Security instead comes entirely from the HMAC-SHA256 signature check
    # below - an unsigned or forged request is rejected before anything is
    # parsed or written.
    async def razorpay_webhook(self, request: Request):
        raw_body_bytes = await request.body()
        signature = request.headers.get("X-Razorpay-Signature", "")

        try:
            raw_body = raw_body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Malformed webhook body.")

        if not self.payment_service.verify_webhook_signature(raw_body, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

        try:
            self.payment_service.handle_webhook_event(raw_body)
        except Exception:
            # A non-2xx response makes Razorpay retry the delivery later - safe
            # to ask for, since processing is idempotent on the event
            # fingerprint. Swallowing this into a fake 200 would silently lose
            # a payment status update instead.
            raise HTTPException(status_code=500, detail="Webhook processing failed.")

        return {"status": "ok"}


payment_api = PaymentApi()
payment_router = payment_api.router
