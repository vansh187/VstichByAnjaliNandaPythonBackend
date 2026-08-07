from datetime import datetime

from pydantic import BaseModel


class SubscribeResponseDTO(BaseModel):
    status: str
    vstitch_subscriber_id: int
    email: str
    created_date: datetime
    updated_date: datetime
