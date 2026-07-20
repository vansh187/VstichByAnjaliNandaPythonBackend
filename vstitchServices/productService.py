from vstitchDatabase.productPersistence import ProductPersistence
from vstitchDTO.productCardResponseDTO import ProductCardResponseDTO
from vstitchDTO.productDetailResponseDTO import ProductDetailResponseDTO, ProductImageDetailDTO, ProductVariantDetailDTO
from vstitchDTO.productListResponseDTO import ProductListResponseDTO
from vstitchServices.localCacheService import local_cache_service

PRODUCT_LIST_CACHE_TTL_SECONDS = 30
PRODUCT_DETAIL_CACHE_TTL_SECONDS = 30


class ProductService:
    """Business logic for browsing the product catalog."""

    def __init__(self):
        self.product_persistence = ProductPersistence()

    def list_products(self, category_id, search, in_stock_only, after_id, limit):
        cache_key = f"products:list:{category_id}:{search}:{in_stock_only}:{after_id}:{limit}"
        cached_response = local_cache_service.get(cache_key)
        if cached_response is not None:
            return cached_response

        rows = self.product_persistence.list_products_page(category_id, search, in_stock_only, after_id, limit)

        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = page_rows[-1]["vstitch_product_id"] if has_more else None

        response = ProductListResponseDTO(
            items=[
                ProductCardResponseDTO(
                    vstitch_product_id=row["vstitch_product_id"],
                    product_name=row["product_name"],
                    category_id=row["vstitch_category_id"],
                    category_name=row["category_name"],
                    min_price=row["min_price"],
                    max_price=row["max_price"],
                    primary_image_url=row["image_url"],
                    available_colors=row["colors"] or [],
                    in_stock=bool(row["in_stock"]),
                )
                for row in page_rows
            ],
            next_cursor=next_cursor,
            has_more=has_more,
        )

        local_cache_service.set(cache_key, response, PRODUCT_LIST_CACHE_TTL_SECONDS)
        return response

    def get_product_detail(self, vstitch_product_id):
        cache_key = f"products:detail:{vstitch_product_id}"
        cached_response = local_cache_service.get(cache_key)
        if cached_response is not None:
            return cached_response

        detail = self.product_persistence.get_product_detail(vstitch_product_id)
        if detail is None:
            raise ValueError(f"Product {vstitch_product_id} was not found.")

        product = detail["product"]
        response = ProductDetailResponseDTO(
            vstitch_product_id=product["vstitch_product_id"],
            product_name=product["product_name"],
            description=product["description"],
            category_id=product["vstitch_category_id"],
            category_name=product["category_name"],
            base_price=product["base_price"],
            variants=[
                ProductVariantDetailDTO(
                    vstitch_product_variant_id=variant["vstitch_product_variant_id"],
                    sku=variant["sku"],
                    size=variant["size"],
                    color=variant["color"],
                    price=variant["price"],
                    stock_quantity=variant["stock_quantity"],
                )
                for variant in detail["variants"]
            ],
            images=[
                ProductImageDetailDTO(
                    image_url=image["image_url"],
                    is_primary=image["is_primary"],
                    display_order=image["display_order"],
                )
                for image in detail["images"]
            ],
        )

        local_cache_service.set(cache_key, response, PRODUCT_DETAIL_CACHE_TTL_SECONDS)
        return response
