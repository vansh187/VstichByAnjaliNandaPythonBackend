from typing import List, Optional

from pydantic import BaseModel


class AdminProductVariantDTO(BaseModel):
    vstitch_product_variant_id: int
    sku: str
    size: str
    color: str
    price: float
    stock_quantity: int
    is_active: bool
    weight_kg: Optional[float]
    length_cm: Optional[float]
    breadth_cm: Optional[float]
    height_cm: Optional[float]


class AdminProductImageDTO(BaseModel):
    image_url: str
    is_primary: bool
    display_order: int


class AdminProductResponseDTO(BaseModel):
    vstitch_product_id: int
    product_name: str
    description: Optional[str]
    category_id: int
    category_name: str
    base_price: float
    is_active: bool
    variants: List[AdminProductVariantDTO]
    images: List[AdminProductImageDTO]


class AdminProductListResponseDTO(BaseModel):
    items: List[AdminProductResponseDTO]
    next_cursor: Optional[int]
    has_more: bool


class CreateProductBatchErrorDTO(BaseModel):
    index: int
    message: str


class CreateProductsBatchResponseDTO(BaseModel):
    created: List[AdminProductResponseDTO]
    errors: List[CreateProductBatchErrorDTO]
