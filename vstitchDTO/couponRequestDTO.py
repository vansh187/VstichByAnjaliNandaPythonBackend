from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

VALID_DISCOUNT_TYPES = ("percentage", "flat")

# VSTITCH_COUPONS columns that are NOT NULL - an explicit null for one of
# these on a PATCH is rejected (see UpdateCouponRequestDTO.
# reject_null_on_required_fields). Every other updatable field
# (min_order_amount, max_discount_amount, usage_limit, valid_until) IS
# nullable in the DB, so an explicit null there is honored as "clear this
# field" instead - deliberately NOT listed here.
COUPON_NON_NULLABLE_FIELDS = ("discount_type", "discount_value", "is_active")


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
    # What the shopper actually applies at checkout - normalized to
    # uppercase here so "festive20" and "FESTIVE20" are always the same
    # coupon, matching how ApplyCouponRequestDTO normalizes the code it
    # looks up.
    coupon_code: str = Field(..., min_length=3, max_length=50)
    discount_type: str
    discount_value: float = Field(..., gt=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, gt=0)
    usage_limit: Optional[int] = Field(default=None, ge=0)
    valid_until: Optional[datetime] = None
    # is_active/valid_from are deliberately not accepted here - every new
    # coupon starts active with valid_from = now(), both server-managed,
    # matching the admin contract's own create-request shape (neither
    # field appears in it). Use PATCH /admin/coupons/{id} to deactivate a
    # coupon afterward.

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
    # All optional, merged onto the current row by CouponService. Unlike
    # the earlier version of this DTO, an explicit null is NOT uniformly
    # rejected here - see COUPON_NON_NULLABLE_FIELDS/
    # reject_null_on_required_fields: only discount_type/discount_value/
    # is_active reject null (they're NOT NULL columns); the four others
    # below are nullable columns, so an explicit null on one of them is a
    # legitimate "clear this field" request (e.g. remove an expiry date or
    # a max-discount cap) and is passed straight through.
    discount_type: Optional[str] = None
    discount_value: Optional[float] = Field(default=None, gt=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, gt=0)
    usage_limit: Optional[int] = Field(default=None, ge=0)
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None
    # coupon_code/valid_from are deliberately not updatable. coupon_code:
    # renaming a code that may already be printed/shared/bookmarked would
    # silently break it for anyone who has it, unlike every other field
    # here, which is safe to change in place - create a new coupon
    # instead. valid_from: server-managed at creation time only, same as
    # CreateCouponRequestDTO.

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
        # "don't change this one") from "field explicitly sent as null" -
        # rejected only for the three NOT NULL columns in
        # COUPON_NON_NULLABLE_FIELDS; every other field's explicit null is
        # valid and handled by CouponService.update_coupon's merge step.
        for field_name in COUPON_NON_NULLABLE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self
