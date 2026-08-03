import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from starlette.concurrency import run_in_threadpool

from vstitchDTO.shipmentRequestDTO import CreateReplaceRequestDTO, CreateReturnRequestDTO
from vstitchDTO.shipmentResponseDTO import CancelOrderResponseDTO, CreateReplaceResponseDTO, CreateReturnResponseDTO
from vstitchServices.authDependency import get_current_user
from vstitchServices.rateLimiter import limiter
from vstitchServices.shipmentService import ShipmentService
from vstitchServices.shiprocketWebhookAuthDependency import require_shiprocket_webhook_key

logger = logging.getLogger(__name__)


class ShipmentApi:
    """Customer-facing shipping endpoints: checkout-time serviceability,
    order tracking, cancellation, and returns. Fulfillment/ops actions (AWB
    assignment, pickup/label/manifest/invoice generation, NDR) are a
    separate, internally-gated router - see shipmentOpsApi.py.
    """

    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route(
            "/shipping/serviceability",
            self.check_serviceability,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/orders/{vstitch_order_id}/tracking",
            self.track_order,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/orders/{vstitch_order_id}/cancel",
            self.cancel_order,
            methods=["POST"],
            response_model=CancelOrderResponseDTO,
        )
        self.router.add_api_route(
            "/orders/{vstitch_order_id}/return",
            self._build_create_return_route(),
            methods=["POST"],
            response_model=CreateReturnResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/orders/{vstitch_order_id}/replace",
            self._build_create_replace_route(),
            methods=["POST"],
            response_model=CreateReplaceResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/shipments/webhook",
            self.shiprocket_webhook,
            methods=["POST"],
            dependencies=[Depends(require_shiprocket_webhook_key)],
        )

    # No auth dependency: this runs on the checkout page before the customer
    # has necessarily done anything account-specific, and it exposes nothing
    # user-specific - only a pincode's serviceability/rate, which Shiprocket
    # itself treats as public information.
    #
    # Sync def, not async: this makes a blocking `requests` call to
    # Shiprocket - see razorpay_webhook in paymentApi.py for why that must
    # never run directly on the event loop. FastAPI dispatches sync def
    # handlers to its worker-thread pool, which is what makes this safe here.
    def check_serviceability(
        self,
        delivery_postcode: str = Query(..., min_length=1, max_length=20),
        weight_kg: float = Query(..., gt=0),
        cash_on_delivery: bool = Query(default=False),
    ):
        try:
            return ShipmentService().check_serviceability(delivery_postcode, weight_kg, cash_on_delivery)
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Something went wrong while checking delivery availability. Please try again.",
            )

    def track_order(
        self,
        vstitch_order_id: int = Path(..., ge=1),
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return ShipmentService().get_tracking_for_order(vstitch_order_id, current_user["vstitch_user_id"])
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Something went wrong while fetching tracking info. Please try again.",
            )

    def cancel_order(
        self,
        vstitch_order_id: int = Path(..., ge=1),
        current_user: dict = Depends(get_current_user),
    ):
        try:
            ShipmentService().cancel_order(vstitch_order_id, current_user["vstitch_user_id"])
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Something went wrong while cancelling your order. Please try again.",
            )
        return CancelOrderResponseDTO(vstitch_order_id=vstitch_order_id, message="Order cancelled.")

    def _build_create_return_route(self):
        # A plain closure, not a bound instance method: slowapi's @limiter.limit
        # inspects the decorated function's own parameter list to find
        # "request" by position, then indexes into the raw call args by that
        # position at request time. A bound method's descriptor protocol
        # sneaks `self` into that positional args tuple, which desyncs it
        # from the "request" position slowapi computed from the *unbound*
        # signature - see loginapi.py's _build_login_route for the full
        # rationale (same pattern, reused here since this route now also
        # needs a bespoke rate limit rather than only the global default).
        #
        # Rate limited: 10/minute per client IP - this endpoint calls out to
        # Shiprocket (cost/abuse surface), unlike most customer read endpoints
        # which rely solely on the global 200/minute default.
        @limiter.limit("10/minute")
        def create_return(
            create_return_request_dto: CreateReturnRequestDTO,
            request: Request,
            vstitch_order_id: int = Path(..., ge=1),
            current_user: dict = Depends(get_current_user),
        ):
            try:
                vstitch_return_order_id, shiprocket_response = ShipmentService().create_return(
                    vstitch_order_id, current_user["vstitch_user_id"], create_return_request_dto.reason
                )
            except ValueError as validation_error:
                raise HTTPException(status_code=409, detail=str(validation_error))
            except Exception:
                raise HTTPException(
                    status_code=502,
                    detail="Something went wrong while creating your return. Please try again.",
                )
            return CreateReturnResponseDTO(
                vstitch_return_order_id=vstitch_return_order_id, shiprocket_response=shiprocket_response
            )

        return create_return

    def _build_create_replace_route(self):
        # Same closure + rate-limit pattern as _build_create_return_route,
        # and for the same reason (Shiprocket-cost abuse surface).
        @limiter.limit("10/minute")
        def create_replace(
            create_replace_request_dto: CreateReplaceRequestDTO,
            request: Request,
            vstitch_order_id: int = Path(..., ge=1),
            current_user: dict = Depends(get_current_user),
        ):
            try:
                vstitch_return_order_id, shiprocket_response = ShipmentService().create_replace(
                    vstitch_order_id,
                    current_user["vstitch_user_id"],
                    create_replace_request_dto.issue_category,
                    create_replace_request_dto.reason,
                    [item.model_dump() for item in create_replace_request_dto.items],
                )
            except ValueError as validation_error:
                raise HTTPException(status_code=409, detail=str(validation_error))
            except Exception:
                raise HTTPException(
                    status_code=502,
                    detail="Something went wrong while creating your replacement request. Please try again.",
                )
            return CreateReplaceResponseDTO(
                vstitch_return_order_id=vstitch_return_order_id, shiprocket_response=shiprocket_response
            )

        return create_replace

    # Shiprocket delivers tracking events here (Settings -> API -> Webhooks,
    # URL = this endpoint, with the same secret as SHIPROCKET_WEBHOOK_API_KEY
    # set as the "x-api-key" value). Always returns 200 on anything short of
    # a bad key - handle_tracking_webhook() itself never raises for expected
    # cases (unknown order, unmapped status, stale delivery), and an
    # unexpected bug here must not turn into Shiprocket endlessly retrying a
    # delivery that will never succeed, so it's caught and logged too.
    #
    # async def + run_in_threadpool, same reasoning as razorpay_webhook in
    # paymentApi.py: handle_tracking_webhook does blocking DB writes, and
    # this route has no other need to be async, so the blocking work is
    # pushed off the shared event loop rather than run directly on it.
    async def shiprocket_webhook(self, request: Request):
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed webhook body.")

        try:
            await run_in_threadpool(ShipmentService().handle_tracking_webhook, payload)
        except Exception:
            # Logs the payload's top-level field names only, never the full
            # payload - it carries customer PII (shipping address, phone)
            # that has no reason to end up in application logs.
            payload_keys = list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
            logger.exception("Shiprocket tracking webhook processing failed. Payload fields: %s", payload_keys)
        return {"status": "ok"}


shipment_api = ShipmentApi()
shipment_router = shipment_api.router
