from fastapi import APIRouter, HTTPException, Query

from vstitchDTO.bestSellersResponseDTO import BestSellersResponseDTO
from vstitchServices.bestSellerService import BestSellerService


class BestSellerApi:
    """Exposes the public /best-sellers endpoint and translates service errors into HTTP responses."""

    def __init__(self):
        self.best_seller_service = BestSellerService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/best-sellers",
            self.list_best_sellers,
            methods=["GET"],
            response_model=BestSellersResponseDTO,
        )

    # Sync def, not async def: same rationale as the other read endpoints -
    # psycopg2 is blocking, so FastAPI's worker-thread dispatch for sync def
    # handlers is what gives real concurrency here (see ConnectionFactory).
    def list_best_sellers(self, limit: int = Query(default=10, ge=1, le=50)):
        try:
            return self.best_seller_service.list_best_sellers(limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading best sellers. Please try again later.",
            )


best_seller_api = BestSellerApi()
best_seller_router = best_seller_api.router
