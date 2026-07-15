from typing import Optional

from pydantic import BaseModel


class CategoryResponseDTO(BaseModel):
    vstitch_category_id: int
    category_name: str
    parent_category_id: Optional[int]
