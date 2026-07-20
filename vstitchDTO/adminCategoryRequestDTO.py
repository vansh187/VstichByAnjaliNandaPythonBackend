from typing import Optional

from pydantic import BaseModel, Field, model_validator

# VStitch_Categories columns that are NOT NULL - a PATCH request must never
# resolve to null on one of these. category_name/is_active are still
# Optional[...] on the DTO below (a client can omit them entirely to leave
# them unchanged), but an explicit `null` for one of them is a different,
# invalid request and has to be rejected here - see
# UpdateCategoryRequestDTO.reject_null_on_required_fields.
CATEGORY_NON_NULLABLE_FIELDS = ("category_name", "is_active")


class CreateCategoryRequestDTO(BaseModel):
    category_name: str = Field(..., min_length=1, max_length=250)
    parent_category_id: Optional[int] = Field(default=None, ge=1)
    image_url: Optional[str] = Field(default=None, max_length=500)


class UpdateCategoryRequestDTO(BaseModel):
    # All optional - the service layer merges whichever fields are supplied
    # onto the category's current row rather than requiring a full replace.
    category_name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    parent_category_id: Optional[int] = Field(default=None, ge=1)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def reject_null_on_required_fields(self):
        # model_fields_set only tells the service layer "was this key present
        # in the request", not "was it non-null" - a client can legally send
        # {"is_active": null} since the field is Optional[bool]. Without this
        # check that null gets merged in as "supplied" and written straight
        # into VStitch_Categories.IsActive/CategoryName, both NOT NULL,
        # surfacing as an uncaught NotNullViolation (a generic 500) instead
        # of a clean 422 here.
        for field_name in CATEGORY_NON_NULLABLE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self
