from pydantic import BaseModel, field_validator

# VStitch_ReturnOrders.Status CHECK-constraint values (vstitch_return_orders.sql) -
# single source of truth here, mirroring how UpdateOrderStatusRequestDTO
# validates against OrderStatus.ALLOWED_TRANSITIONS' keys instead of a
# second hardcoded list.
VALID_RETURN_STATUSES = ("requested", "approved", "rejected", "picked_up", "completed", "cancelled")


class UpdateReturnStatusRequestDTO(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value not in VALID_RETURN_STATUSES:
            raise ValueError(f"status must be one of {VALID_RETURN_STATUSES}.")
        return value
