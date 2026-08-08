from fastapi import APIRouter, HTTPException, Query, Request

from vstitchDTO.applyCouponDTO import ApplyCouponRequestDTO, ApplyCouponResponseDTO
from vstitchDTO.couponResponseDTO import AvailableCouponsResponseDTO
from vstitchServices.couponService import CouponNotFoundError, CouponService
from vstitchServices.rateLimiter import limiter


class CouponApi:
    """Exposes the customer-facing coupon endpoints:
    - GET /coupons - price-based coupon list for the checkout screen. No
      auth (same public-read shape as /products) - the shopper doesn't
      need to be logged in to see what discounts exist.
    - POST /coupons/apply - validates a specific code against the current
      order total and returns the discount to apply. Also unauthenticated
      (a guest cart can preview a coupon before login/checkout), so it's
      rate-limited against code-guessing the same way /login is rate-limited
      against password-guessing.
    """

    def __init__(self):
        self.coupon_service = CouponService()
        self.router = APIRouter()
        self.router.add_api_route(
            "/coupons", self.list_available_coupons, methods=["GET"], response_model=AvailableCouponsResponseDTO
        )
        self.router.add_api_route(
            "/coupons/apply",
            self._build_apply_coupon_route(),
            methods=["POST"],
            response_model=ApplyCouponResponseDTO,
        )

    def list_available_coupons(self, order_amount: float = Query(default=0, ge=0)):
        try:
            return self.coupon_service.list_available_coupons(order_amount)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading coupons. Please try again later.",
            )

    def _build_apply_coupon_route(self):
        # A plain closure, not a bound instance method - see LoginApi.
        # _build_login_route's comment (loginapi.py) for why @limiter.limit
        # requires this.
        coupon_service = self.coupon_service

        # Rate limited: 20 attempts/minute per IP - looser than /login's
        # 5/minute since mistyping a coupon code during normal checkout is
        # far more common than mistyping a password, but still bounded
        # against brute-forcing an unknown/inactive code.
        @limiter.limit("20/minute")
        def apply_coupon(apply_coupon_request_dto: ApplyCouponRequestDTO, request: Request):
            try:
                return coupon_service.apply_coupon(apply_coupon_request_dto)
            except CouponNotFoundError as not_found_error:
                raise HTTPException(status_code=404, detail=str(not_found_error))
            except ValueError as conflict_error:
                # Coupon exists but can't be applied right now (inactive,
                # order total below its minimum) - same 409 "business-rule
                # conflict" convention OrderApi.create_order uses for
                # stock-related ValueErrors, not a 422 (nothing about the
                # request body itself is malformed).
                raise HTTPException(status_code=409, detail=str(conflict_error))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Something went wrong while applying the coupon. Please try again later.",
                )

        return apply_coupon


coupon_api = CouponApi()
coupon_router = coupon_api.router
