from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

# VStitch_Products / VStitch_ProductVariants columns that are NOT NULL - see
# UpdateProductRequestDTO.reject_null_on_required_fields /
# UpdateProductVariantRequestDTO.reject_null_on_required_fields for why an
# explicit `null` on one of these has to be rejected at request-validation
# time rather than reaching the DB as an uncaught NotNullViolation.
PRODUCT_NON_NULLABLE_FIELDS = ("product_name", "base_price", "is_active")
VARIANT_NON_NULLABLE_FIELDS = ("sku", "size", "color", "price", "stock_quantity", "is_active")


class CreateProductVariantRequestDTO(BaseModel):
    sku: str = Field(..., min_length=1, max_length=250)
    size: str = Field(default="Standard", min_length=1, max_length=50)
    color: str = Field(default="Standard", min_length=1, max_length=50)
    price: float = Field(..., ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True
    # Nullable, matching VStitch_ProductVariants' own shipping-dimension
    # columns - required by Shiprocket at shipment-creation time, but not
    # required to create the variant/product itself (a catalog-data task,
    # per migrations/0004's own comment).
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None


class CreateProductImageRequestDTO(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)
    is_primary: bool = False
    display_order: int = 0


class CreateProductRequestDTO(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=250)
    description: Optional[str] = None
    category_id: int = Field(..., ge=1)
    base_price: float = Field(..., ge=0)
    is_active: bool = True
    variants: List[CreateProductVariantRequestDTO] = Field(..., min_length=1)
    images: List[CreateProductImageRequestDTO] = Field(default_factory=list)


class CreateProductsBatchRequestDTO(BaseModel):
    products: List[CreateProductRequestDTO] = Field(..., min_length=1, max_length=100)


class UpdateProductRequestDTO(BaseModel):
    # All optional, merged onto the current row - same pattern as
    # UpdateCategoryRequestDTO (see its comment for why plain None isn't
    # enough to detect "field omitted").
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    description: Optional[str] = None
    category_id: Optional[int] = Field(default=None, ge=1)
    base_price: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def reject_null_on_required_fields(self):
        for field_name in PRODUCT_NON_NULLABLE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self


class UpdateProductVariantRequestDTO(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=250)
    size: Optional[str] = Field(default=None, min_length=1, max_length=50)
    color: Optional[str] = Field(default=None, min_length=1, max_length=50)
    price: Optional[float] = Field(default=None, ge=0)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None

    @model_validator(mode="after")
    def reject_null_on_required_fields(self):
        for field_name in VARIANT_NON_NULLABLE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self
