from typing import List

from fastapi import APIRouter, HTTPException

from vstitchDTO.categoryResponseDTO import CategoryResponseDTO
from vstitchServices.categoryService import CategoryService


class CategoryApi:
    """Exposes the public category-listing endpoint and translates service errors into HTTP responses."""

    def __init__(self):
        self.category_service = CategoryService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/categories",
            self.list_categories,
            methods=["GET"],
            response_model=List[CategoryResponseDTO],
        )

    def list_categories(self):
        try:
            return self.category_service.list_categories()
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading categories. Please try again later.",
            )


category_api = CategoryApi()
category_router = category_api.router
