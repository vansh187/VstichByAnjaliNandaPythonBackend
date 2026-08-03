from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CreateCustomizationRequestResponseDTO(BaseModel):
    vstitch_customization_request_id: int
    vstitch_product_id: int
    vstitch_product_variant_id: int
    status: str
    created_at: datetime


class CustomizationRequestDetailResponseDTO(BaseModel):
    """Shape returned by GET /customization-requests (a user's own
    submissions) - the same fields as the create response plus enough of
    the original submission to show in a "My Customization Requests" list
    without a second round trip per row.
    """

    vstitch_customization_request_id: int
    vstitch_product_id: int
    vstitch_product_variant_id: int
    product_name: str
    size: str
    color: str
    customer_name: str
    customer_phone: str
    bust_in: float
    waist_in: float
    hips_in: float
    shoulder_in: float
    sleeve_length_in: float
    dress_length_in: float
    notes: Optional[str]
    status: str
    created_at: datetime


class CustomizationRequestListResponseDTO(BaseModel):
    requests: List[CustomizationRequestDetailResponseDTO]
