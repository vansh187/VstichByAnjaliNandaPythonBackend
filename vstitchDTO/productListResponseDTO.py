from typing import List, Optional

from pydantic import BaseModel

from vstitchDTO.productCardResponseDTO import ProductCardResponseDTO


class ProductListResponseDTO(BaseModel):
    items: List[ProductCardResponseDTO]
    next_cursor: Optional[int]
    has_more: bool
