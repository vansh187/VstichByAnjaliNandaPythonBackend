from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AdminReturnResponseDTO(BaseModel):
    vstitch_return_order_id: int
    vstitch_order_id: int
    customer_name: str
    customer_email: str
    reason: str
    status: str
    shiprocket_return_order_id: Optional[int]
    shiprocket_shipment_id: Optional[int]
    created_date: datetime


class AdminReturnListResponseDTO(BaseModel):
    returns: List[AdminReturnResponseDTO]
    has_more: bool
    next_cursor: Optional[int]
