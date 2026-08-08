from typing import List, Optional

from pydantic import BaseModel


class CouponResponseDTO(BaseModel):
    """Admin-facing shape - includes is_active, unlike AvailableCouponDTO."""

    vstitch_coupon_id: int
    coupon_name: str
    coupon_code: str
    coupon_description: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    is_active: bool


class CouponListResponseDTO(BaseModel):
    items: List[CouponResponseDTO]
    next_cursor: Optional[int] = None
    has_more: bool = False


class AvailableCouponDTO(BaseModel):
    """Customer-facing shape for GET /coupons - no is_active, since only
    already-active coupons are ever returned to this endpoint."""

    coupon_code: str
    coupon_name: str
    coupon_description: str
    discount_type: str
    discount_value: float
    min_order_amount: float


class AvailableCouponsResponseDTO(BaseModel):
    items: List[AvailableCouponDTO]
