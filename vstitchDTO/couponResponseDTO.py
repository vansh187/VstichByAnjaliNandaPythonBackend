from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CouponResponseDTO(BaseModel):
    """Admin-facing shape - matches the marketing-panel contract's field
    names exactly. GET /admin/coupons returns a bare list of these (no
    pagination wrapper), per the contract's own response shape."""

    vstitch_coupon_id: int
    coupon_code: str
    discount_type: str
    discount_value: float
    min_order_amount: Optional[float]
    max_discount_amount: Optional[float]
    usage_limit: Optional[int]
    used_count: int
    valid_from: datetime
    valid_until: Optional[datetime]
    is_active: bool
    created_date: datetime


class AvailableCouponDTO(BaseModel):
    """Customer-facing shape for GET /coupons - only what's needed to
    display/select a coupon at checkout. No used_count/valid_from/
    created_date - a shopper doesn't need redemption-tracking or audit
    detail, only what the coupon is worth and any cap on it."""

    coupon_code: str
    discount_type: str
    discount_value: float
    min_order_amount: Optional[float]
    max_discount_amount: Optional[float]


class AvailableCouponsResponseDTO(BaseModel):
    items: list[AvailableCouponDTO]
