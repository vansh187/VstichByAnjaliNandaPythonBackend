from pydantic import BaseModel, field_validator

from vstitchServices.orderStatus import OrderStatus


class UpdateOrderStatusRequestDTO(BaseModel):
    order_status: str

    @field_validator("order_status")
    @classmethod
    def validate_order_status(cls, value):
        # Membership check against OrderStatus.ALLOWED_TRANSITIONS' keys, not
        # a hardcoded string list here - one source of truth for the valid
        # VStitch_Orders.OrderStatus CHECK-constraint values, so this can
        # never drift out of sync with orderStatus.py. Fails at request
        # validation (422) rather than reaching the DB and relying on its
        # CHECK constraint to catch a bad value.
        valid_statuses = tuple(OrderStatus.ALLOWED_TRANSITIONS.keys())
        if value not in valid_statuses:
            raise ValueError(f"order_status must be one of {valid_statuses}.")
        return value
