from typing import Any, Dict

from pydantic import BaseModel


class CreateReturnResponseDTO(BaseModel):
    vstitch_return_order_id: int
    shiprocket_response: Dict[str, Any]


class CreateReplaceResponseDTO(BaseModel):
    # Deliberately the same shape as CreateReturnResponseDTO: a replace
    # request is stored as a VStitch_ReturnOrders row too (RequestType=
    # 'replace'), so vstitch_return_order_id here is an id in that same
    # table/id-space, not a separate "replace order" table.
    vstitch_return_order_id: int
    shiprocket_response: Dict[str, Any]


class CancelOrderResponseDTO(BaseModel):
    vstitch_order_id: int
    message: str
