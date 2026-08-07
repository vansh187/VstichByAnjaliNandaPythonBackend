from fastapi import APIRouter, HTTPException, Request

from vstitchDTO.subscribeRequestDTO import SubscribeRequestDTO
from vstitchDTO.subscribeResponseDTO import SubscribeResponseDTO
from vstitchServices.rateLimiter import limiter
from vstitchServices.subscriberService import SubscriberService, SubscriptionError


class SubscriberApi:
    """Exposes POST /subscribe - the newsletter "Subscribe" form. No auth
    (reachable by any site visitor, logged in or not), same public-write
    shape as /customization-interest.
    """

    def __init__(self):
        self.subscriber_service = SubscriberService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/subscribe",
            self._build_subscribe_route(),
            methods=["POST"],
            response_model=SubscribeResponseDTO,
            status_code=201,
        )

    def _build_subscribe_route(self):
        # A plain closure, not a bound instance method - see LoginApi.
        # _build_login_route's comment (loginapi.py) for why @limiter.limit
        # requires this.
        #
        # Rate limited: 5 submissions/minute per client IP - same
        # unauthenticated-write abuse profile as /signup and
        # /customization-interest.
        subscriber_service = self.subscriber_service

        @limiter.limit("5/minute")
        def subscribe(request_dto: SubscribeRequestDTO, request: Request):
            try:
                return subscriber_service.subscribe(request_dto)
            except SubscriptionError as subscription_error:
                raise HTTPException(status_code=500, detail=str(subscription_error))
            except Exception:
                # Catch-all so no unanticipated bug can ever surface as a
                # raw, unhandled exception to an unauthenticated caller -
                # always a safe, generic 500 instead.
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while subscribing. Please try again later.",
                )

        return subscribe


subscriber_api = SubscriberApi()
subscriber_router = subscriber_api.router
