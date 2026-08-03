from fastapi import APIRouter, Depends, HTTPException, Path, Request

from vstitchDTO.customizationRequestDTO import CreateCustomizationRequestDTO
from vstitchDTO.customizationResponseDTO import (
    CreateCustomizationRequestResponseDTO,
    CustomizationRequestListResponseDTO,
)
from vstitchServices.authDependency import get_current_user, get_current_user_optional
from vstitchServices.customizationRequestService import CustomizationRequestService
from vstitchServices.rateLimiter import limiter


class CustomizationRequestApi:
    """Exposes the "Request bespoke measurements" endpoints: submitting a
    request from a product page (reachable while logged out), and a logged-
    in shopper listing their own past submissions.
    """

    def __init__(self):
        self.customization_request_service = CustomizationRequestService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/products/{vstitch_product_id}/variants/{vstitch_product_variant_id}/customization-requests",
            self._build_create_customization_request_route(),
            methods=["POST"],
            response_model=CreateCustomizationRequestResponseDTO,
            status_code=201,
        )
        self.router.add_api_route(
            "/customization-requests",
            self.list_customization_requests,
            methods=["GET"],
            response_model=CustomizationRequestListResponseDTO,
        )

    def _build_create_customization_request_route(self):
        # A plain closure, not a bound instance method - see LoginApi.
        # _build_login_route's comment (loginapi.py) for why @limiter.limit
        # requires this: slowapi inspects the decorated function's own
        # parameter list to find "request" by position, and a bound
        # method's implicit `self` would desync that position.
        #
        # Rate limited: 5 submissions/minute per client IP - this endpoint
        # is reachable with no login (no account-creation friction the way
        # /orders has), so it's the same unauthenticated-write abuse
        # profile as /signup, not the "already has an account" profile of
        # most other POST endpoints.
        customization_request_service = self.customization_request_service

        @limiter.limit("5/minute")
        def create_customization_request(
            request_dto: CreateCustomizationRequestDTO,
            request: Request,
            vstitch_product_id: int = Path(..., ge=1),
            vstitch_product_variant_id: int = Path(..., ge=1),
            current_user: dict = Depends(get_current_user_optional),
        ):
            vstitch_user_id = current_user["vstitch_user_id"] if current_user is not None else None
            try:
                return customization_request_service.create_request(
                    vstitch_product_id, vstitch_product_variant_id, request_dto, vstitch_user_id
                )
            except ValueError as not_found_error:
                raise HTTPException(status_code=404, detail=str(not_found_error))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while submitting your customization request. Please try again later.",
                )

        return create_customization_request

    # vstitch_user_id is taken from the verified JWT, never from a
    # client-supplied id - same IDOR rationale as OrderApi.list_orders:
    # "my requests" is deliberately not "requests by user_id".
    def list_customization_requests(self, current_user: dict = Depends(get_current_user)):
        try:
            requests = self.customization_request_service.list_requests_for_user(current_user["vstitch_user_id"])
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading your customization requests. Please try again later.",
            )
        return CustomizationRequestListResponseDTO(requests=requests)


customization_request_api = CustomizationRequestApi()
customization_request_router = customization_request_api.router
