from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class OrderItemResponseDTO(BaseModel):
    # Optional/None only right after order placement (CreateOrderResponseDTO),
    # since the freshly-inserted item rows' own ids aren't returned by the
    # bulk insert - always populated once an order is read back via
    # GET /orders (OrderDetailResponseDTO), where it's needed to reference a
    # specific line item in a replace request.
    vstitch_order_item_id: Optional[int] = None
    # Optional: VStitch_OrderItems.VstitchProductVariantId is
    # ON DELETE SET NULL - an order placed against a variant that was later
    # deleted from the catalog legitimately has NULL here. The order-item
    # snapshot fields below (product_name/size/color/unit_price) are what
    # actually describe what was purchased regardless.
    vstitch_product_variant_id: Optional[int] = None
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
    delivered_date: Optional[datetime]
    can_return: bool
    can_replace: bool
    items: List[OrderItemResponseDTO]


class OrderListResponseDTO(BaseModel):
    orders: List[OrderDetailResponseDTO]
    has_more: bool
    next_cursor: Optional[int]
