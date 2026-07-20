from vstitchDatabase.productPersistence import ProductPersistence
from vstitchDTO.adminProductResponseDTO import (
    AdminProductImageDTO,
    AdminProductListResponseDTO,
    AdminProductResponseDTO,
    AdminProductVariantDTO,
    CreateProductBatchErrorDTO,
    CreateProductsBatchResponseDTO,
)
from vstitchServices.localCacheService import local_cache_service


class AdminProductService:
    """Business logic for the admin product/variant-management endpoints."""

    def __init__(self):
        self.product_persistence = ProductPersistence()

    def list_products(self, after_id, limit):
        """One page of products, each with its full variant/image detail -
        fetched via two bulk queries (WHERE product_id = ANY(page_ids)) up
        front rather than looping get_full_product_for_admin per row, so a
        page's round-trip count stays constant instead of scaling 3x with
        page size against the shared, small connection pool."""
        rows = self.product_persistence.list_products_for_admin(after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]

        product_ids = [row["vstitch_product_id"] for row in page_rows]
        variants_by_product_id = self.product_persistence.get_variants_for_products_admin(product_ids)
        images_by_product_id = self.product_persistence.get_images_for_products_admin(product_ids)

        items = [
            self._to_product_dto(
                {
                    "product": row,
                    "variants": variants_by_product_id.get(row["vstitch_product_id"], []),
                    "images": images_by_product_id.get(row["vstitch_product_id"], []),
                }
            )
            for row in page_rows
        ]
        next_cursor = page_rows[-1]["vstitch_product_id"] if has_more and page_rows else None
        return AdminProductListResponseDTO(items=items, next_cursor=next_cursor, has_more=has_more)

    def create_products_batch(self, create_products_batch_request_dto, admin_username):
        """Each product is its own persistence call (its own DB transaction) -
        a bad row (duplicate SKU, invalid category) fails and rolls back
        only that product; the loop continues and reports it in errors[]
        rather than aborting the whole batch, per the admin contract's own
        "partial success is expected" requirement.
        """
        created = []
        errors = []
        for index, product in enumerate(create_products_batch_request_dto.products):
            try:
                variants = [variant.model_dump() for variant in product.variants]
                images = [image.model_dump() for image in product.images]
                full_product = self.product_persistence.create_product_with_variants(
                    product.product_name,
                    product.description,
                    product.category_id,
                    product.base_price,
                    product.is_active,
                    variants,
                    images,
                    f"admin:{admin_username}",
                )
                created.append(self._to_product_dto(full_product))
            except ValueError as validation_error:
                errors.append(CreateProductBatchErrorDTO(index=index, message=str(validation_error)))

        self._invalidate_cache()
        return CreateProductsBatchResponseDTO(created=created, errors=errors)

    def get_product(self, vstitch_product_id):
        full_product = self.product_persistence.get_full_product_for_admin(vstitch_product_id)
        if full_product is None:
            raise ValueError(f"Product {vstitch_product_id} was not found.")
        return self._to_product_dto(full_product)

    def update_product(self, vstitch_product_id, update_product_request_dto, admin_username):
        current = self.product_persistence.get_product_for_admin(vstitch_product_id)
        if current is None:
            raise ValueError(f"Product {vstitch_product_id} was not found.")

        supplied = update_product_request_dto.model_fields_set
        product_name = update_product_request_dto.product_name if "product_name" in supplied else current["product_name"]
        description = update_product_request_dto.description if "description" in supplied else current["description"]
        category_id = update_product_request_dto.category_id if "category_id" in supplied else current["vstitch_category_id"]
        base_price = update_product_request_dto.base_price if "base_price" in supplied else current["base_price"]
        is_active = update_product_request_dto.is_active if "is_active" in supplied else current["is_active"]

        was_updated = self.product_persistence.update_product(
            vstitch_product_id, product_name, description, category_id, base_price, is_active, f"admin:{admin_username}"
        )
        if not was_updated:
            raise ValueError(f"Product {vstitch_product_id} was not found.")
        self._invalidate_cache(vstitch_product_id)
        return self.get_product(vstitch_product_id)

    def delete_product(self, vstitch_product_id, admin_username):
        """Soft-delete (IsActive=FALSE) - see soft_delete_product's comment
        in productPersistence.py for why this is never a real DELETE."""
        was_deleted = self.product_persistence.soft_delete_product(vstitch_product_id, f"admin:{admin_username}")
        if not was_deleted:
            raise ValueError(f"Product {vstitch_product_id} was not found.")
        self._invalidate_cache(vstitch_product_id)

    def add_variant(self, vstitch_product_id, create_variant_request_dto, admin_username):
        row = self.product_persistence.add_variant(
            vstitch_product_id, create_variant_request_dto.model_dump(), f"admin:{admin_username}"
        )
        self._invalidate_cache(vstitch_product_id)
        return self._to_variant_dto(row)

    def update_variant(self, vstitch_product_variant_id, update_variant_request_dto, admin_username):
        current = self.product_persistence.get_variant_for_admin(vstitch_product_variant_id)
        if current is None:
            raise ValueError(f"Product variant {vstitch_product_variant_id} was not found.")

        supplied = update_variant_request_dto.model_fields_set
        merged = {
            field: getattr(update_variant_request_dto, field) if field in supplied else current[field]
            for field in ("sku", "size", "color", "price", "stock_quantity", "is_active",
                          "weight_kg", "length_cm", "breadth_cm", "height_cm")
        }

        was_updated = self.product_persistence.update_variant(
            vstitch_product_variant_id, merged, f"admin:{admin_username}"
        )
        if not was_updated:
            raise ValueError(f"Product variant {vstitch_product_variant_id} was not found.")
        self._invalidate_cache(current["vstitch_product_id"])
        return self._to_variant_dto(self.product_persistence.get_variant_for_admin(vstitch_product_variant_id))

    def delete_variant(self, vstitch_product_variant_id, admin_username):
        """Soft-delete (IsActive=FALSE) - never a real DELETE, see
        soft_delete_variant's comment in productPersistence.py (a real
        delete would cascade-wipe the variant out of every live cart)."""
        current = self.product_persistence.get_variant_for_admin(vstitch_product_variant_id)
        if current is None:
            raise ValueError(f"Product variant {vstitch_product_variant_id} was not found.")
        self.product_persistence.soft_delete_variant(vstitch_product_variant_id, f"admin:{admin_username}")
        self._invalidate_cache(current["vstitch_product_id"])

    @staticmethod
    def _invalidate_cache(vstitch_product_id=None):
        # Matches the existing precedent in orderService.py's stock-decrement
        # cache invalidation. Known limitation, not solved here (see
        # AdminCategoryService._invalidate_cache's comment): this cache is
        # in-process only.
        if vstitch_product_id is not None:
            local_cache_service.delete(f"products:detail:{vstitch_product_id}")
        local_cache_service.clear_prefix("products:list:")

    @staticmethod
    def _to_variant_dto(row):
        return AdminProductVariantDTO(
            vstitch_product_variant_id=row["vstitch_product_variant_id"],
            sku=row["sku"],
            size=row["size"],
            color=row["color"],
            price=row["price"],
            stock_quantity=row["stock_quantity"],
            is_active=row["is_active"],
            weight_kg=row["weight_kg"],
            length_cm=row["length_cm"],
            breadth_cm=row["breadth_cm"],
            height_cm=row["height_cm"],
        )

    @classmethod
    def _to_product_dto(cls, full_product):
        product_row = full_product["product"]
        return AdminProductResponseDTO(
            vstitch_product_id=product_row["vstitch_product_id"],
            product_name=product_row["product_name"],
            description=product_row["description"],
            category_id=product_row["vstitch_category_id"],
            category_name=product_row["category_name"],
            base_price=product_row["base_price"],
            is_active=product_row["is_active"],
            variants=[cls._to_variant_dto(variant_row) for variant_row in full_product["variants"]],
            images=[
                AdminProductImageDTO(
                    image_url=image_row["image_url"],
                    is_primary=image_row["is_primary"],
                    display_order=image_row["display_order"],
                )
                for image_row in full_product["images"]
            ],
        )
