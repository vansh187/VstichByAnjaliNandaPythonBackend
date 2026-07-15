from psycopg2.extras import execute_values

from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader

ORDER_ITEM_INSERT_TEMPLATE = "(%s, %s, %s, %s, %s, %s, %s, %s)"


class OrderPersistence:
    """Database logic backing order placement against VStitch_Orders/VStitch_OrderItems."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("order_queries.yaml")

    def get_variants_for_order(self, vstitch_product_variant_ids):
        """Fetches every requested variant in a single round trip, keyed by id."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_variants_for_order"),
                    (vstitch_product_variant_ids,),
                )
                variant_rows = cursor.fetchall()
            column_names = (
                "vstitch_product_variant_id",
                "vstitch_product_id",
                "product_name",
                "size",
                "color",
                "price",
                "stock_quantity",
                "is_active",
            )
            return {row[0]: dict(zip(column_names, row)) for row in variant_rows}

    def create_cod_order(
        self,
        vstitch_user_id,
        total_amount,
        shipping_recipient_name,
        shipping_address_line1,
        shipping_address_line2,
        shipping_city,
        shipping_state,
        shipping_postal_code,
        shipping_country,
        shipping_phone_number,
        created_by_ip_address,
        order_items,
    ):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_order"),
                    (
                        vstitch_user_id,
                        total_amount,
                        shipping_recipient_name,
                        shipping_address_line1,
                        shipping_address_line2,
                        shipping_city,
                        shipping_state,
                        shipping_postal_code,
                        shipping_country,
                        shipping_phone_number,
                        created_by_ip_address,
                    ),
                )
                vstitch_order_id, order_status, payment_method, inserted_total_amount, _created_date = cursor.fetchone()

                # Single UPDATE...FROM UNNEST decrements every line's stock atomically
                # instead of one round trip per item; order_items is pre-deduped by
                # variant id (see OrderService), so each variant appears at most once
                # here - required for this batched form to target each row once.
                variant_ids = [order_item["vstitch_product_variant_id"] for order_item in order_items]
                quantities = [order_item["quantity"] for order_item in order_items]
                cursor.execute(
                    self.query_loader.get_query("decrement_variant_stock_bulk"),
                    (variant_ids, quantities),
                )
                remaining_stock_by_variant_id = {row[0]: row[1] for row in cursor.fetchall()}
                for order_item in order_items:
                    if order_item["vstitch_product_variant_id"] not in remaining_stock_by_variant_id:
                        raise ValueError(
                            f"Insufficient stock for {order_item['product_name_snapshot']}."
                        )

                execute_values(
                    cursor,
                    self.query_loader.get_query("insert_order_items_bulk"),
                    [
                        (
                            vstitch_order_id,
                            order_item["vstitch_product_variant_id"],
                            order_item["product_name_snapshot"],
                            order_item["size_snapshot"],
                            order_item["color_snapshot"],
                            order_item["unit_price_snapshot"],
                            order_item["quantity"],
                            created_by_ip_address,
                        )
                        for order_item in order_items
                    ],
                    template=ORDER_ITEM_INSERT_TEMPLATE,
                )

            connection.commit()
            return (
                vstitch_order_id,
                order_status,
                payment_method,
                inserted_total_amount,
                remaining_stock_by_variant_id,
            )
