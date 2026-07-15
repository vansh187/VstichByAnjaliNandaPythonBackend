from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from vstitchDTO.createOrderRequestDTO import CreateOrderRequestDTO
from vstitchDTO.orderResponseDTO import CreateOrderResponseDTO, OrderListResponseDTO
from vstitchServices.authDependency import get_current_user
from vstitchServices.orderService import OrderService


class OrderApi:
    """Exposes the /orders endpoints and translates service errors into HTTP responses."""

    def __init__(self):
        self.order_service = OrderService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/orders",
            self.create_order,
            methods=["POST"],
            response_model=CreateOrderResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/orders",
            self.list_orders,
            methods=["GET"],
            response_model=OrderListResponseDTO,
        )

    # Deliberately a sync def, not async def: psycopg2 is a blocking driver, so an
    # async def here would run that blocking DB work directly on the event loop
    # thread and stall every other request. FastAPI already dispatches sync def
    # handlers to a worker-thread pool, which is what gives real concurrency here
    # (see ConnectionFactory's ThreadedConnectionPool for the matching rationale).
    def create_order(
        self,
        create_order_request_dto: CreateOrderRequestDTO,
        request: Request,
        current_user: dict = Depends(get_current_user),
    ):
        client_ip_address = request.client.host if request.client else "unknown"
        try:
            return self.order_service.place_cod_order(
                create_order_request_dto, current_user["vstitch_user_id"], client_ip_address
            )
        except ValueError as validation_error:
            raise HTTPException(status_code=409, detail=str(validation_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while placing the order. Please try again later.",
            )

    # Sync def for the same reason as create_order above - psycopg2 blocks, and
    # FastAPI's worker-thread dispatch is what gives real concurrency here.
    #
    # vstitch_user_id is taken from the verified JWT, never from a client-supplied
    # id - accepting an id here would let any authenticated user read anyone
    # else's order history (IDOR). "Get my orders" is deliberately not
    # "get orders by user_id".
    def list_orders(
        self,
        before_id: Optional[int] = Query(default=None, ge=1),
        limit: int = Query(default=20, ge=1, le=50),
        current_user: dict = Depends(get_current_user),
    ):
        try:
            return self.order_service.list_orders_for_user(current_user["vstitch_user_id"], before_id, limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading your orders. Please try again later.",
            )


order_api = OrderApi()
order_router = order_api.router
