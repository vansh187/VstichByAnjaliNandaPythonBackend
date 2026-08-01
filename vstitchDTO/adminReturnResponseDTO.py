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
    request_type: str
    shiprocket_return_order_id: Optional[int]
    shiprocket_shipment_id: Optional[int]
    created_date: datetime
    # Only meaningful on the response to a status update that transitioned to
    # 'completed' - None on every other read (list, or a transition to any
    # other status), since no refund is triggered for those.
    refund_triggered: Optional[bool] = None


class AdminReturnListResponseDTO(BaseModel):
    returns: List[AdminReturnResponseDTO]
    has_more: bool
    next_cursor: Optional[int]
