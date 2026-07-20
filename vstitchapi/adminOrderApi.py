from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from vstitchDTO.adminOrderRequestDTO import VALID_PAYMENT_METHODS, UpdateOrderStatusRequestDTO
from vstitchDTO.adminOrderResponseDTO import AdminOrderListResponseDTO, AdminOrderResponseDTO
from vstitchServices.adminAuthDependency import get_current_admin
from vstitchServices.adminOrderService import AdminOrderService
from vstitchServices.orderStatus import OrderStatus


class AdminOrderApi:
    """Exposes the /admin/orders endpoints - cross-customer order listing,
    detail, and status override. The whole router requires an admin bearer
    token (Depends(get_current_admin) on the APIRouter itself), same
    mechanism shipmentOpsApi.py uses for its ops-key gate.
    """

    def __init__(self):
        self.admin_order_service = AdminOrderService()
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/orders",
            self.list_orders,
            methods=["GET"],
            response_model=AdminOrderListResponseDTO,
        )
        self.router.add_api_route(
            "/orders/{vstitch_order_id}",
            self.get_order,
            methods=["GET"],
            response_model=AdminOrderResponseDTO,
        )
        self.router.add_api_route(
            "/orders/{vstitch_order_id}/status",
            self.update_order_status,
            methods=["PATCH"],
            response_model=AdminOrderResponseDTO,
        )

    # Sync def, not async def: psycopg2 is a blocking driver - see orderapi.py's
    # create_order for the full rationale, repeated at every DB-backed handler
    # in this codebase rather than re-explained per file.
    def list_orders(
        self,
        status: Optional[str] = Query(default=None),
        payment_method: Optional[str] = Query(default=None),
        search: Optional[str] = Query(default=None, max_length=250),
        after_id: Optional[int] = Query(default=None, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        # Validated here rather than left to the SQL's exact-match filter,
        # which would otherwise silently return zero rows on a typo/wrong
        # case instead of a clear 422 - same "validate at the request
        # boundary" convention as UpdateOrderStatusRequestDTO.
        if status is not None and status not in OrderStatus.ALLOWED_TRANSITIONS:
            raise HTTPException(
                status_code=422,
                detail=f"status must be one of {tuple(OrderStatus.ALLOWED_TRANSITIONS.keys())}.",
            )
        if payment_method is not None and payment_method not in VALID_PAYMENT_METHODS:
            raise HTTPException(
                status_code=422,
                detail=f"payment_method must be one of {VALID_PAYMENT_METHODS}.",
            )
        try:
            return self.admin_order_service.list_orders(status, payment_method, search, after_id, limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading orders. Please try again later.",
            )

    def get_order(self, vstitch_order_id: int = Path(..., ge=1)):
        try:
            return self.admin_order_service.get_order(vstitch_order_id)
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading the order. Please try again later.",
            )

    def update_order_status(
        self,
        update_order_status_request_dto: UpdateOrderStatusRequestDTO,
        vstitch_order_id: int = Path(..., ge=1),
        current_admin: dict = Depends(get_current_admin),
    ):
        try:
            return self.admin_order_service.update_order_status(
                vstitch_order_id,
                update_order_status_request_dto.order_status,
                current_admin["admin_username"],
            )
        except ValueError as validation_error:
            raise HTTPException(status_code=404, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while updating the order status. Please try again later.",
            )


admin_order_api = AdminOrderApi()
admin_order_router = admin_order_api.router
