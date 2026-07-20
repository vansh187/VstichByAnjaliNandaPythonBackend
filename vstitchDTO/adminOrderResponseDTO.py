from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AdminOrderItemDTO(BaseModel):
    vstitch_order_item_id: int
    product_name_snapshot: str
    size_snapshot: Optional[str]
    color_snapshot: Optional[str]
    unit_price_snapshot: float
    quantity: int


class AdminOrderResponseDTO(BaseModel):
    vstitch_order_id: int
    vstitch_user_id: int
    customer_name: str
    customer_email: str
    order_status: str
    payment_method: str
    total_amount: float
    shipping_recipient_name: str
    shipping_address_line1: str
    shipping_address_line2: Optional[str]
    shipping_city: str
    shipping_state: str
    shipping_postal_code: str
    shipping_country: str
    shipping_phone_number: str
    awb_code: Optional[str]
    courier_name: Optional[str]
    created_date: datetime
    items: List[AdminOrderItemDTO]


class AdminOrderListResponseDTO(BaseModel):
    orders: List[AdminOrderResponseDTO]
    has_more: bool
    next_cursor: Optional[int]
