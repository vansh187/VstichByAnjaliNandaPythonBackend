from fastapi import APIRouter, HTTPException, Request

from vstitchDTO.customizationInterestDTO import CreateCustomizationInterestDTO
from vstitchDTO.customizationInterestResponseDTO import CreateCustomizationInterestResponseDTO
from vstitchServices.customizationInterestService import CustomizationInterestService
from vstitchServices.rateLimiter import limiter


class CustomizationInterestApi:
    """Exposes POST /customization-interest - the VStitch AI widget's "Need
    a Custom Outfit?" lead form. No auth (reachable by any site visitor,
    logged in or not), same public-write shape as
    /products/{id}/variants/{id}/customization-requests.
    """

    def __init__(self):
        self.customization_interest_service = CustomizationInterestService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/customization-interest",
            self._build_create_customization_interest_route(),
            methods=["POST"],
            response_model=CreateCustomizationInterestResponseDTO,
            status_code=201,
        )

    def _build_create_customization_interest_route(self):
        # A plain closure, not a bound instance method - see LoginApi.
        # _build_login_route's comment (loginapi.py) for why @limiter.limit
        # requires this.
        #
        # Rate limited: 5 submissions/minute per client IP - same
        # unauthenticated-write abuse profile as /signup and
        # /customization-requests (this form needs no account either).
        customization_interest_service = self.customization_interest_service

        @limiter.limit("5/minute")
        def create_customization_interest(
            request_dto: CreateCustomizationInterestDTO,
            request: Request,
        ):
            try:
                customization_interest_service.submit_interest(request_dto)
            except Exception:
                # Covers both the one expected failure mode
                # (CustomizationInterestEmailError - Resend down/
                # misconfigured/rejected the send) and any unanticipated
                # bug: both are reported identically, as a plain 500 with a
                # safe, generic message - matches the spec's frontend
                # contract ("couldn't send right now, please try WhatsApp
                # instead") rather than leaking internal error text to an
                # unauthenticated caller.
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while sending your request. Please try again later.",
                )
            return CreateCustomizationInterestResponseDTO(status="sent")

        return create_customization_interest


customization_interest_api = CustomizationInterestApi()
customization_interest_router = customization_interest_api.router
