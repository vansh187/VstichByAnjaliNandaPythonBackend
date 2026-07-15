from typing import List, Optional

from pydantic import BaseModel, Field

from vstitchDTO.orderItemRequestDTO import OrderItemRequestDTO


class CreateOrderRequestDTO(BaseModel):
    shipping_recipient_name: str = Field(..., min_length=1, max_length=250)
    shipping_address_line1: str = Field(..., min_length=1, max_length=250)
    shipping_address_line2: Optional[str] = Field(default=None, max_length=250)
    shipping_city: str = Field(..., min_length=1, max_length=250)
    shipping_state: str = Field(..., min_length=1, max_length=250)
    shipping_postal_code: str = Field(..., min_length=1, max_length=20)
    shipping_country: str = Field(..., min_length=1, max_length=250)
    shipping_phone_number: str = Field(..., min_length=7, max_length=250)
    items: List[OrderItemRequestDTO] = Field(..., min_length=1, max_length=50)
