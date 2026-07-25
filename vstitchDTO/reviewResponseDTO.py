from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ReviewResponseDTO(BaseModel):
    vstitch_review_id: int
    vstitch_product_id: int
    rating: int
    review_text: Optional[str]
    created_date: datetime
    updated_date: Optional[datetime]


class ReviewListItemDTO(BaseModel):
    vstitch_review_id: int
    reviewer_name: str
    rating: int
    review_text: Optional[str]
    created_date: datetime


class ReviewListResponseDTO(BaseModel):
    average_rating: Optional[float]
    review_count: int
    reviews: List[ReviewListItemDTO]
    has_more: bool
    next_cursor: Optional[int]
