from fastapi import APIRouter, Depends, HTTPException, Request

from vstitchDTO.createOrderRequestDTO import CreateOrderRequestDTO
from vstitchDTO.orderResponseDTO import CreateOrderResponseDTO
from vstitchServices.authDependency import get_current_user
from vstitchServices.orderService import OrderService


class OrderApi:
    """Exposes the /orders endpoint and translates service errors into HTTP responses."""

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


order_api = OrderApi()
order_router = order_api.router
