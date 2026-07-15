from pydantic import BaseModel, Field


class OrderItemRequestDTO(BaseModel):
    vstitch_product_variant_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=100)
