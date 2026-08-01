from typing import List

from pydantic import BaseModel, Field, field_validator


class CreateReturnRequestDTO(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


# VStitch_ReturnOrderItems.IssueCategory CHECK-constraint values
# (vstitch_return_order_items, added by migration 0010) - single source of
# truth here, same pattern as adminReturnRequestDTO.py's VALID_RETURN_STATUSES.
VALID_REPLACE_ISSUE_CATEGORIES = ("size_issue", "defect")


class ReplaceItemRequestDTO(BaseModel):
    vstitch_order_item_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1, le=100)


class CreateReplaceRequestDTO(BaseModel):
    issue_category: str = Field(..., min_length=1, max_length=20)
    reason: str = Field(..., min_length=1, max_length=500)
    items: List[ReplaceItemRequestDTO] = Field(..., min_length=1, max_length=50)

    @field_validator("issue_category")
    @classmethod
    def validate_issue_category(cls, value):
        if value not in VALID_REPLACE_ISSUE_CATEGORIES:
            raise ValueError(f"issue_category must be one of {VALID_REPLACE_ISSUE_CATEGORIES}.")
        return value


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
