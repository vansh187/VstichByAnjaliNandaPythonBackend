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
