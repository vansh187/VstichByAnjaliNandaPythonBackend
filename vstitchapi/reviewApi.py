from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status

from vstitchDTO.reviewRequestDTO import CreateOrUpdateReviewRequestDTO
from vstitchDTO.reviewResponseDTO import ReviewListResponseDTO, ReviewResponseDTO
from vstitchServices.authDependency import get_current_user
from vstitchServices.reviewService import ReviewService


class ReviewApi:
    """Exposes the /products/{vstitch_product_id}/reviews endpoints and
    translates service errors into HTTP responses."""

    def __init__(self):
        self.review_service = ReviewService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/products/{vstitch_product_id}/reviews",
            self.create_or_update_review,
            methods=["POST"],
            response_model=ReviewResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/products/{vstitch_product_id}/reviews",
            self.list_reviews,
            methods=["GET"],
            response_model=ReviewListResponseDTO,
        )

    # Sync def, not async def: psycopg2 is a blocking driver - see
    # orderapi.py's create_order for the full rationale, repeated at every
    # DB-backed handler in this codebase rather than re-explained per file.
    #
    # vstitch_user_id is taken from the verified JWT, never a client-supplied
    # id - same IDOR guard as list_orders in orderapi.py. Upserts (see
    # ReviewService.upsert_review): a second submission from the calling
    # user updates their existing review rather than erroring, since
    # VStitch_Reviews allows only one review per (user, product).
    def create_or_update_review(
        self,
        create_or_update_review_request_dto: CreateOrUpdateReviewRequestDTO,
        response: Response,
        request: Request,
        vstitch_product_id: int = Path(..., ge=1),
        current_user: dict = Depends(get_current_user),
    ):
        # Same created_by/updated_by convention as signup/orders - the
        # client IP, not a username, for every customer-initiated write.
        client_ip_address = request.client.host if request.client else "unknown"
        try:
            review, was_created = self.review_service.upsert_review(
                vstitch_product_id,
                current_user["vstitch_user_id"],
                create_or_update_review_request_dto,
                client_ip_address,
            )
        except ValueError as not_found_error:
            raise HTTPException(status_code=404, detail=str(not_found_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while saving your review. Please try again later.",
            )
        if not was_created:
            response.status_code = status.HTTP_200_OK
        return review

    def list_reviews(
        self,
        vstitch_product_id: int = Path(..., ge=1),
        before_id: Optional[int] = Query(default=None, ge=1),
        limit: int = Query(default=20, ge=1, le=50),
    ):
        try:
            return self.review_service.list_reviews_for_product(vstitch_product_id, before_id, limit)
        except ValueError as not_found_error:
            raise HTTPException(status_code=404, detail=str(not_found_error))
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading reviews. Please try again later.",
            )


review_api = ReviewApi()
review_router = review_api.router
