from pydantic import BaseModel, Field


class CreateReturnRequestDTO(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class AssignAwbRequestDTO(BaseModel):
    vstitch_order_id: int = Field(..., ge=1)


class ShipmentBatchRequestDTO(BaseModel):
    """Shared shape for the ops endpoints that operate on a batch of
    VStitch orders at once (generate pickup/label/manifest/invoice)."""

    vstitch_order_ids: list[int] = Field(..., min_length=1, max_length=100)


class NdrActionRequestDTO(BaseModel):
    # Shiprocket's own /ndr action payload shape wasn't provided beyond the
    # endpoint - passed through as-is (action: "reattempt" or "return", plus
    # whatever per-AWB detail Shiprocket's NDR docs require) rather than
    # guessed field-by-field.
    ndr_action_payload: dict = Field(..., min_length=1)
