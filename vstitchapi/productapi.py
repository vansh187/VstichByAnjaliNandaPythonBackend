from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from vstitchDTO.productDetailResponseDTO import ProductDetailResponseDTO
from vstitchDTO.productListResponseDTO import ProductListResponseDTO
from vstitchServices.productService import ProductService


class ProductApi:
    """Exposes the public catalog-browsing endpoints and translates service errors into HTTP responses."""

    def __init__(self):
        self.product_service = ProductService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/products",
            self.list_products,
            methods=["GET"],
            response_model=ProductListResponseDTO,
        )
        self.router.add_api_route(
            "/products/{product_id}",
            self.get_product_detail,
            methods=["GET"],
            response_model=ProductDetailResponseDTO,
        )

    # Deliberately sync def, not async def: the underlying DB calls run through
    # psycopg2, a blocking driver. FastAPI dispatches sync def handlers to a
    # worker-thread pool automatically, giving real concurrency; an async def
    # here would instead run that blocking work on the event loop thread and
    # stall every other in-flight request (see ConnectionFactory for the
    # matching rationale on the connection pool itself).
    def list_products(
        self,
        category_id: Optional[int] = Query(default=None, gt=0),
        search: Optional[str] = Query(default=None, max_length=250),
        in_stock_only: bool = Query(default=False),
        after_id: Optional[int] = Query(default=None, gt=0),
        limit: int = Query(default=20, ge=1, le=50),
    ):
        try:
            return self.product_service.list_products(category_id, search, in_stock_only, after_id, limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading products. Please try again later.",
            )

    def get_product_detail(self, product_id: int):
        try:
            return self.product_service.get_product_detail(product_id)
        except ValueError as not_found_error:
            raise HTTPException(status_code=404, detail=str(not_found_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading this product. Please try again later.",
            )


product_api = ProductApi()
product_router = product_api.router
