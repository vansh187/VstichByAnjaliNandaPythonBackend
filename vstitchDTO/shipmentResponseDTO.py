from typing import Any, Dict

from pydantic import BaseModel


class CreateReturnResponseDTO(BaseModel):
    vstitch_return_order_id: int
    shiprocket_response: Dict[str, Any]


class CancelOrderResponseDTO(BaseModel):
    vstitch_order_id: int
    message: str
