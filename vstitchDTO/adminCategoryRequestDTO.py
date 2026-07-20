from typing import Optional

from pydantic import BaseModel, Field


class CreateCategoryRequestDTO(BaseModel):
    category_name: str = Field(..., min_length=1, max_length=250)
    parent_category_id: Optional[int] = Field(default=None, ge=1)
    image_url: Optional[str] = Field(default=None, max_length=500)


class UpdateCategoryRequestDTO(BaseModel):
    # All optional - the service layer merges whichever fields are supplied
    # onto the category's current row rather than requiring a full replace.
    category_name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    parent_category_id: Optional[int] = Field(default=None, ge=1)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
