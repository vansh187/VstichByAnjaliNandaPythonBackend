from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

VALID_DISCOUNT_TYPES = ("percentage", "flat")

# VSTITCH_COUPONS columns that are NOT NULL - same "reject an explicit null
# on a partial update" pattern as adminProductRequestDTO.py's
# PRODUCT_NON_NULLABLE_FIELDS (see UpdateCouponRequestDTO below).
COUPON_NON_NULLABLE_FIELDS = (
    "coupon_name",
    "coupon_description",
    "discount_type",
    "discount_value",
    "min_order_amount",
    "is_active",
)


def _normalize_coupon_code(value):
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("coupon_code cannot be blank.")
    return normalized


def _validate_discount_type(value):
    if value not in VALID_DISCOUNT_TYPES:
        raise ValueError(f"discount_type must be one of {VALID_DISCOUNT_TYPES}.")
    return value


class CreateCouponRequestDTO(BaseModel):
    coupon_name: str = Field(..., min_length=1, max_length=250)
    # What the shopper actually applies at checkout - normalized to
    # uppercase here so "festive20" and "FESTIVE20" are always the same
    # coupon, matching how ApplyCouponRequestDTO normalizes the code it
    # looks up.
    coupon_code: str = Field(..., min_length=3, max_length=50)
    coupon_description: str = Field(..., min_length=1, max_length=500)
    discount_type: str
    discount_value: float = Field(..., gt=0)
    min_order_amount: float = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("coupon_code")
    @classmethod
    def validate_coupon_code(cls, value):
        return _normalize_coupon_code(value)

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type_field(cls, value):
        return _validate_discount_type(value)

    @field_validator("discount_value")
    @classmethod
    def validate_percentage_range(cls, value, info):
        # field_validator runs in declaration order, so discount_type has
        # already been validated/normalized by the time this runs and is
        # available in info.data.
        if info.data.get("discount_type") == "percentage" and value > 100:
            raise ValueError("A percentage discount_value cannot exceed 100.")
        return value


class UpdateCouponRequestDTO(BaseModel):
    # All optional, merged onto the current row by CouponService - same
    # pattern as UpdateProductRequestDTO. coupon_code is deliberately not
    # updatable: renaming a code that may already be printed/shared/
    # bookmarked would silently break it for anyone who has it, unlike
    # every other field here, which is safe to change in place. Create a
    # new coupon instead.
    coupon_name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    coupon_description: Optional[str] = Field(default=None, min_length=1, max_length=500)
    discount_type: Optional[str] = None
    discount_value: Optional[float] = Field(default=None, gt=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type_field(cls, value):
        if value is None:
            return value
        return _validate_discount_type(value)

    @model_validator(mode="after")
    def reject_null_on_required_fields(self):
        # Same pattern as UpdateProductRequestDTO.reject_null_on_required_fields:
        # model_fields_set distinguishes "field omitted" (fine - means
        # "don't change this one") from "field explicitly sent as null"
        # (rejected - every one of these columns is NOT NULL in
        # VSTITCH_COUPONS, so a caller-supplied null would otherwise reach
        # the DB as an uncaught NotNullViolation).
        for field_name in COUPON_NON_NULLABLE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self
