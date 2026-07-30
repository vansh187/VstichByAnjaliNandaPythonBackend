from typing import Optional

from pydantic import BaseModel


class AdminCategoryResponseDTO(BaseModel):
    vstitch_category_id: int
    category_name: str
    parent_category_id: Optional[int]
    image_url: Optional[str]
    is_active: bool
