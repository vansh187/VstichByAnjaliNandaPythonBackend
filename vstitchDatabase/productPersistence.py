import psycopg2.errors

from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.invalidReferenceError import InvalidReferenceError
from vstitchDatabase.queryLoader import QueryLoader
from vstitchDatabase.uniqueConstraintError import translate_unique_violation

PRODUCT_CARD_COLUMNS = (
    "vstitch_product_id",
    "product_name",
    "vstitch_category_id",
    "category_name",
    "min_price",
    "max_price",
    "in_stock",
    "colors",
    "image_url",
)

ADMIN_PRODUCT_COLUMNS = (
    "vstitch_product_id",
    "product_name",
    "description",
    "vstitch_category_id",
    "category_name",
    "base_price",
    "is_active",
)

ADMIN_VARIANT_COLUMNS = (
    "vstitch_product_variant_id",
    "sku",
    "size",
    "color",
    "price",
    "stock_quantity",
    "is_active",
    "weight_kg",
    "length_cm",
    "breadth_cm",
    "height_cm",
)

ADMIN_IMAGE_COLUMNS = ("image_url", "is_primary", "display_order")

# Constraint names from vstitch_product_variants.sql - translated into a
# human-readable message when INSERT/UPDATE hits either one.
VARIANT_UNIQUE_CONSTRAINT_MESSAGES = {
    "uq_variants_sku": "A variant with this SKU already exists.",
    "uq_variants_product_size_color": "This product already has a variant with the same size and color.",
}

DIMENSION_CHECK_VIOLATION_MESSAGE = (
    "Invalid shipping dimensions - weight_kg must be greater than 0, and length_cm/breadth_cm/"
    "height_cm must each be at least 0.5, when provided."
)


class ProductPersistence:
    """Database logic backing catalog browsing against VStitch_Products/Variants/Images."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("product_queries.yaml")

    def list_products_page(self, category_id, search, in_stock_only, after_id, limit):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("list_products_page"),
                    {
                        "category_id": category_id,
                        "search": f"%{search}%" if search else None,
                        "in_stock_only": in_stock_only,
                        "after_id": after_id,
                        "limit_plus_one": limit + 1,
                    },
                )
                rows = cursor.fetchall()
            return [dict(zip(PRODUCT_CARD_COLUMNS, row)) for row in rows]

    def get_products_by_ids(self, vstitch_product_ids):
        """Bulk card-shape fetch for an arbitrary set of product ids - used
        wherever a ranked/curated id list needs to become full card data (best
        sellers today; related products later). Does not preserve the input
        order - callers that care about ranking must reorder the result."""
        if not vstitch_product_ids:
            return {}
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_products_by_ids"),
                    (list(vstitch_product_ids),),
                )
                rows = cursor.fetchall()
            return {row[0]: dict(zip(PRODUCT_CARD_COLUMNS, row)) for row in rows}

    def get_product_detail(self, vstitch_product_id):
        """Fetches the product row plus its variants/images in one connection
        checkout - three small indexed queries for a single-product deep read
        is simpler than one mega-query, and just as fast at this scale."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_product_by_id"),
                    (vstitch_product_id,),
                )
                product_row = cursor.fetchone()
                if product_row is None:
                    return None

                cursor.execute(
                    self.query_loader.get_query("get_variants_for_product"),
                    (vstitch_product_id,),
                )
                variant_rows = cursor.fetchall()

                cursor.execute(
                    self.query_loader.get_query("get_images_for_product"),
                    (vstitch_product_id,),
                )
                image_rows = cursor.fetchall()

            product_columns = (
                "vstitch_product_id",
                "product_name",
                "description",
                "vstitch_category_id",
                "category_name",
                "base_price",
            )
            variant_columns = ("vstitch_product_variant_id", "sku", "size", "color", "price", "stock_quantity")
            image_columns = ("image_url", "is_primary", "display_order")

            return {
                "product": dict(zip(product_columns, product_row)),
                "variants": [dict(zip(variant_columns, row)) for row in variant_rows],
                "images": [dict(zip(image_columns, row)) for row in image_rows],
            }

    def count_low_stock_variants(self, low_stock_threshold):
        """Number of active variants at or below the low-stock threshold -
        backs the admin revenue dashboard's low_stock_count."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("low_stock_variant_count"), (low_stock_threshold,))
                return cursor.fetchone()[0]

    # --- Admin: product management -----------------------------------------

    def list_products_for_admin(self, after_id, limit_plus_one):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("list_products_admin"),
                    {"after_id": after_id, "limit_plus_one": limit_plus_one},
                )
                rows = cursor.fetchall()
            return [dict(zip(ADMIN_PRODUCT_COLUMNS, row)) for row in rows]

    def get_product_for_admin(self, vstitch_product_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_product_by_id_admin"), (vstitch_product_id,))
                row = cursor.fetchone()
            return dict(zip(ADMIN_PRODUCT_COLUMNS, row)) if row is not None else None

    def get_variants_for_product_admin(self, vstitch_product_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_variants_for_product_admin"), (vstitch_product_id,))
                rows = cursor.fetchall()
            return [dict(zip(ADMIN_VARIANT_COLUMNS, row)) for row in rows]

    def get_images_for_product_admin(self, vstitch_product_id):
        # Same query/shape as the public get_images_for_product - images
        # aren't soft-deletable in this admin API, so no admin-only variant
        # of this query is needed.
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_images_for_product"), (vstitch_product_id,))
                rows = cursor.fetchall()
            return [dict(zip(ADMIN_IMAGE_COLUMNS, row)) for row in rows]

    def get_variants_for_products_admin(self, vstitch_product_ids):
        """Bulk counterpart to get_variants_for_product_admin - one query for
        an entire page of products instead of one query per product. Used by
        AdminProductService.list_products so a page of N products costs a
        constant 3 round trips (list + this + get_images_for_products_admin)
        instead of 1 + 3*N - the small connection pool is shared with every
        customer-facing endpoint, so an admin browsing a large product list
        must not be able to serialize hundreds of pool checkouts into one
        request."""
        if not vstitch_product_ids:
            return {}
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_variants_for_products_admin"), (list(vstitch_product_ids),)
                )
                rows = cursor.fetchall()
            variants_by_product_id = {}
            for row in rows:
                variants_by_product_id.setdefault(row[0], []).append(dict(zip(ADMIN_VARIANT_COLUMNS, row[1:])))
            return variants_by_product_id

    def get_images_for_products_admin(self, vstitch_product_ids):
        """Bulk counterpart to get_images_for_product_admin - see
        get_variants_for_products_admin's comment for why this exists."""
        if not vstitch_product_ids:
            return {}
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_images_for_products_admin"), (list(vstitch_product_ids),)
                )
                rows = cursor.fetchall()
            images_by_product_id = {}
            for row in rows:
                images_by_product_id.setdefault(row[0], []).append(dict(zip(ADMIN_IMAGE_COLUMNS, row[1:])))
            return images_by_product_id

    def create_product_with_variants(
        self, product_name, description, category_id, base_price, is_active, variants, images, created_by
    ):
        """One full transaction for one product - the product row, every
        variant, and every image, or none of it. Used once per product in
        an admin batch-create call (see AdminProductService.create_products_batch)
        so a failure on THIS product's own connection/transaction rolls
        back only this product, never anything already committed for a
        previous product in the same batch.

        Raises UniqueConstraintError on a SKU or (product, size, color)
        collision, or ValueError for an invalid category_id (FK violation)
        or an out-of-range shipping dimension (CHECK violation) - either
        way this product's own transaction rolls back cleanly.
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("insert_product"),
                        {
                            "product_name": product_name,
                            "description": description,
                            "category_id": category_id,
                            "base_price": base_price,
                            "is_active": is_active,
                            "created_by": created_by,
                        },
                    )
                    vstitch_product_id = cursor.fetchone()[0]

                    variant_ids = []
                    for variant in variants:
                        cursor.execute(
                            self.query_loader.get_query("insert_variant"),
                            {
                                "vstitch_product_id": vstitch_product_id,
                                "sku": variant["sku"],
                                "size": variant["size"],
                                "color": variant["color"],
                                "price": variant["price"],
                                "stock_quantity": variant["stock_quantity"],
                                "is_active": variant["is_active"],
                                "weight_kg": variant["weight_kg"],
                                "length_cm": variant["length_cm"],
                                "breadth_cm": variant["breadth_cm"],
                                "height_cm": variant["height_cm"],
                                "created_by": created_by,
                            },
                        )
                        variant_ids.append(cursor.fetchone()[0])

                    for image in images:
                        cursor.execute(
                            self.query_loader.get_query("insert_image"),
                            {
                                "vstitch_product_id": vstitch_product_id,
                                "vstitch_product_variant_id": None,
                                "image_url": image["image_url"],
                                "is_primary": image["is_primary"],
                                "display_order": image["display_order"],
                                "created_by": created_by,
                            },
                        )
                except psycopg2.errors.UniqueViolation as unique_violation:
                    connection.rollback()
                    raise translate_unique_violation(
                        unique_violation, VARIANT_UNIQUE_CONSTRAINT_MESSAGES, "A variant with conflicting details already exists."
                    ) from unique_violation
                except psycopg2.errors.ForeignKeyViolation as fk_violation:
                    connection.rollback()
                    raise InvalidReferenceError(f"Category {category_id} does not exist.") from fk_violation
                except psycopg2.errors.CheckViolation as check_violation:
                    connection.rollback()
                    raise InvalidReferenceError(DIMENSION_CHECK_VIOLATION_MESSAGE) from check_violation
            connection.commit()

        return self.get_full_product_for_admin(vstitch_product_id)

    def get_full_product_for_admin(self, vstitch_product_id):
        """product + variants + images, admin shape - the read-back used
        after every admin product write, and by GET /admin/products/{id}
        indirectly via AdminProductService."""
        product_row = self.get_product_for_admin(vstitch_product_id)
        if product_row is None:
            return None
        return {
            "product": product_row,
            "variants": self.get_variants_for_product_admin(vstitch_product_id),
            "images": self.get_images_for_product_admin(vstitch_product_id),
        }

    def update_product(self, vstitch_product_id, product_name, description, category_id, base_price, is_active, updated_by):
        """Full-row update, same merge-in-service-layer pattern as
        update_category. Returns None if the product doesn't exist, raises
        ValueError for an invalid category_id."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("update_product"),
                        {
                            "vstitch_product_id": vstitch_product_id,
                            "product_name": product_name,
                            "description": description,
                            "category_id": category_id,
                            "base_price": base_price,
                            "is_active": is_active,
                            "updated_by": updated_by,
                        },
                    )
                except psycopg2.errors.ForeignKeyViolation as fk_violation:
                    connection.rollback()
                    raise InvalidReferenceError(f"Category {category_id} does not exist.") from fk_violation
                row = cursor.fetchone()
            connection.commit()
            return row is not None

    def soft_delete_product(self, vstitch_product_id, updated_by):
        """Sets IsActive=FALSE - never a real DELETE, see soft_delete_product's
        comment in product_queries.yaml. Returns True if the product existed."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("soft_delete_product"),
                    {"vstitch_product_id": vstitch_product_id, "updated_by": updated_by},
                )
                row = cursor.fetchone()
            connection.commit()
            return row is not None

    def add_variant(self, vstitch_product_id, variant, created_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("insert_variant"),
                        {
                            "vstitch_product_id": vstitch_product_id,
                            "sku": variant["sku"],
                            "size": variant["size"],
                            "color": variant["color"],
                            "price": variant["price"],
                            "stock_quantity": variant["stock_quantity"],
                            "is_active": variant["is_active"],
                            "weight_kg": variant["weight_kg"],
                            "length_cm": variant["length_cm"],
                            "breadth_cm": variant["breadth_cm"],
                            "height_cm": variant["height_cm"],
                            "created_by": created_by,
                        },
                    )
                except psycopg2.errors.UniqueViolation as unique_violation:
                    connection.rollback()
                    raise translate_unique_violation(
                        unique_violation, VARIANT_UNIQUE_CONSTRAINT_MESSAGES, "A variant with conflicting details already exists."
                    ) from unique_violation
                except psycopg2.errors.ForeignKeyViolation as fk_violation:
                    connection.rollback()
                    raise InvalidReferenceError(f"Product {vstitch_product_id} does not exist.") from fk_violation
                except psycopg2.errors.CheckViolation as check_violation:
                    connection.rollback()
                    raise InvalidReferenceError(DIMENSION_CHECK_VIOLATION_MESSAGE) from check_violation
                vstitch_product_variant_id = cursor.fetchone()[0]
            connection.commit()
        # Fresh connection/cursor for the read-back, not the one just closed
        # by the `with connection.cursor()` block above - reusing a closed
        # cursor raises "cursor already closed".
        return self.get_variant_for_admin(vstitch_product_variant_id)

    def get_variant_for_admin(self, vstitch_product_variant_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_variant_by_id_admin"), (vstitch_product_variant_id,))
                row = cursor.fetchone()
            if row is None:
                return None
            columns = ("vstitch_product_variant_id", "vstitch_product_id") + ADMIN_VARIANT_COLUMNS[1:]
            return dict(zip(columns, row))

    def update_variant(self, vstitch_product_variant_id, variant, updated_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("update_variant"),
                        {
                            "vstitch_product_variant_id": vstitch_product_variant_id,
                            "sku": variant["sku"],
                            "size": variant["size"],
                            "color": variant["color"],
                            "price": variant["price"],
                            "stock_quantity": variant["stock_quantity"],
                            "is_active": variant["is_active"],
                            "weight_kg": variant["weight_kg"],
                            "length_cm": variant["length_cm"],
                            "breadth_cm": variant["breadth_cm"],
                            "height_cm": variant["height_cm"],
                            "updated_by": updated_by,
                        },
                    )
                except psycopg2.errors.UniqueViolation as unique_violation:
                    connection.rollback()
                    raise translate_unique_violation(
                        unique_violation, VARIANT_UNIQUE_CONSTRAINT_MESSAGES, "A variant with conflicting details already exists."
                    ) from unique_violation
                except psycopg2.errors.CheckViolation as check_violation:
                    connection.rollback()
                    raise InvalidReferenceError(DIMENSION_CHECK_VIOLATION_MESSAGE) from check_violation
                row = cursor.fetchone()
            connection.commit()
            return row is not None

    def soft_delete_variant(self, vstitch_product_variant_id, updated_by):
        """Sets IsActive=FALSE - never a real DELETE, see soft_delete_variant's
        comment in product_queries.yaml (VStitch_CartItems cascades on a
        real delete). Returns True if the variant existed."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("soft_delete_variant"),
                    {"vstitch_product_variant_id": vstitch_product_variant_id, "updated_by": updated_by},
                )
                row = cursor.fetchone()
            connection.commit()
            return row is not None
