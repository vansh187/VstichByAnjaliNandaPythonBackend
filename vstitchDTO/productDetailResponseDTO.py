from typing import List, Optional

from pydantic import BaseModel


class ProductVariantDetailDTO(BaseModel):
    vstitch_product_variant_id: int
    sku: str
    size: str
    color: str
    price: float
    stock_quantity: int


class ProductImageDetailDTO(BaseModel):
    image_url: str
    is_primary: bool
    display_order: int


class ProductDetailResponseDTO(BaseModel):
    vstitch_product_id: int
    product_name: str
    description: Optional[str]
    category_id: int
    category_name: str
    base_price: float
    variants: List[ProductVariantDetailDTO]
    images: List[ProductImageDetailDTO]
