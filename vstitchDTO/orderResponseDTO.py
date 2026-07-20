from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class OrderItemResponseDTO(BaseModel):
    vstitch_product_variant_id: int
    product_name: str
    size: Optional[str]
    color: Optional[str]
    unit_price: float
    quantity: int
    line_total: float


class CreateOrderResponseDTO(BaseModel):
    vstitch_order_id: int
    order_status: str
    payment_method: str
    total_amount: float
    items: List[OrderItemResponseDTO]
    message: str


class OrderDetailResponseDTO(BaseModel):
    vstitch_order_id: int
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
    created_date: datetime
    awb_code: Optional[str]
    items: List[OrderItemResponseDTO]


class OrderListResponseDTO(BaseModel):
    orders: List[OrderDetailResponseDTO]
    has_more: bool
    next_cursor: Optional[int]
