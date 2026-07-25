from typing import Optional

from pydantic import BaseModel, Field


class CreateOrUpdateReviewRequestDTO(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = Field(default=None, max_length=2000)
