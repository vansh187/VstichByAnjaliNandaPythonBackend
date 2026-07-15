from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


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
            column_names = (
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
            return [dict(zip(column_names, row)) for row in rows]

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
