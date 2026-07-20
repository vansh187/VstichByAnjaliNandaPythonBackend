from typing import List, Optional

from pydantic import BaseModel


class ProductCardResponseDTO(BaseModel):
    vstitch_product_id: int
    product_name: str
    category_id: int
    category_name: str
    min_price: float
    max_price: float
    primary_image_url: Optional[str]
    available_colors: List[str]
    in_stock: bool
