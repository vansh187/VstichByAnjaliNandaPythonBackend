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

    def get_orders_for_user(self, vstitch_user_id, before_id, limit_plus_one):
        """Fetches one page of a user's order headers, newest first, keyset-paginated
        on VstitchOrderId (< before_id). Requests limit_plus_one rows so the caller
        can detect has_more without a separate COUNT query."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_orders_for_user"),
                    {
                        "vstitch_user_id": vstitch_user_id,
                        "before_id": before_id,
                        "limit_plus_one": limit_plus_one,
                    },
                )
                order_rows = cursor.fetchall()
            column_names = (
                "vstitch_order_id",
                "order_status",
                "payment_method",
                "total_amount",
                "shipping_recipient_name",
                "shipping_address_line1",
                "shipping_address_line2",
                "shipping_city",
                "shipping_state",
                "shipping_postal_code",
                "shipping_country",
                "shipping_phone_number",
                "created_date",
            )
            return [dict(zip(column_names, row)) for row in order_rows]

    def get_order_items_for_orders(self, vstitch_order_ids):
        """Bulk-fetches line items for a page of orders in one round trip, keyed by
        order id, instead of one query per order."""
        if not vstitch_order_ids:
            return {}
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_order_items_for_orders"),
                    (vstitch_order_ids,),
                )
                item_rows = cursor.fetchall()
            items_by_order_id = {}
            for row in item_rows:
                items_by_order_id.setdefault(row[0], []).append(
                    {
                        "vstitch_product_variant_id": row[1],
                        "product_name": row[2],
                        "size": row[3],
                        "color": row[4],
                        "unit_price": row[5],
                        "quantity": row[6],
                    }
                )
            return items_by_order_id

    def get_order_for_shipment(self, vstitch_order_id):
        """Fetches everything a Shiprocket create-order call needs for one
        order: the header (address/contact/payment) plus its line items with
        each item's live SKU/weight/dimensions joined in from
        VStitch_ProductVariants. Returns None if the order itself doesn't
        exist; a present order always has at least one item row (order items
        are inserted in the same transaction as the order).
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_order_header_for_shipment"),
                    (vstitch_order_id,),
                )
                header_row = cursor.fetchone()
                if header_row is None:
                    return None

                cursor.execute(
                    self.query_loader.get_query("get_order_items_for_shipment"),
                    (vstitch_order_id,),
                )
                item_rows = cursor.fetchall()

            header_column_names = (
                "vstitch_order_id",
                "payment_method",
                "total_amount",
                "shipping_recipient_name",
                "shipping_address_line1",
                "shipping_address_line2",
                "shipping_city",
                "shipping_state",
                "shipping_postal_code",
                "shipping_country",
                "shipping_phone_number",
                "created_date",
                "email",
            )
            item_column_names = (
                "vstitch_order_item_id",
                "product_name",
                "unit_price",
                "quantity",
                "sku",
                "weight_kg",
                "length_cm",
                "breadth_cm",
                "height_cm",
            )
            order = dict(zip(header_column_names, header_row))
            order["items"] = [dict(zip(item_column_names, row)) for row in item_rows]
            return order

    def save_shiprocket_shipment_ids(self, vstitch_order_id, shiprocket_order_id, shiprocket_shipment_id, updated_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("save_shiprocket_shipment_ids"),
                    {
                        "vstitch_order_id": vstitch_order_id,
                        "shiprocket_order_id": shiprocket_order_id,
                        "shiprocket_shipment_id": shiprocket_shipment_id,
                        "updated_by": updated_by,
                    },
                )
            connection.commit()

    def save_awb_details(self, vstitch_order_id, awb_code, courier_name, updated_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("save_awb_details"),
                    {
                        "vstitch_order_id": vstitch_order_id,
                        "awb_code": awb_code,
                        "courier_name": courier_name,
                        "updated_by": updated_by,
                    },
                )
            connection.commit()

    def get_order_for_tracking(self, vstitch_order_id):
        """Fetches just the identifiers a tracking/cancel/AWB call needs -
        including VstitchUserId, so the caller can verify the requesting user
        actually owns this order before doing anything with it (IDOR guard).
        Returns None if the order doesn't exist.
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_order_for_tracking"),
                    (vstitch_order_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            column_names = (
                "vstitch_order_id",
                "vstitch_user_id",
                "order_status",
                "shiprocket_order_id",
                "shiprocket_shipment_id",
                "awb_code",
            )
            return dict(zip(column_names, row))

    def find_order_by_shiprocket_order_id(self, shiprocket_order_id):
        """Looks up which VStitch order a Shiprocket tracking webhook refers
        to - webhooks are correlated by Shiprocket's own order id, not ours.
        Returns None if no order has this Shiprocket order id (nothing to
        update - not every webhook necessarily corresponds to a known order,
        e.g. a delivery from before this integration existed).
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("find_order_by_shiprocket_order_id"),
                    (shiprocket_order_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return {"vstitch_order_id": row[0], "order_status": row[1]}

    def update_order_status(self, vstitch_order_id, new_status, old_statuses, updated_by):
        """Guarded OrderStatus transition with no side effects beyond the
        status column itself - unlike cancel_order_with_restock, this never
        restocks, since it's used for forward-pipeline progress (confirmed,
        processing, shipped, ...) where nothing should be returned to stock.
        Returns True if the row actually transitioned.
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("update_order_status_guarded"),
                    {
                        "new_status": new_status,
                        "updated_by": updated_by,
                        "vstitch_order_id": vstitch_order_id,
                        "old_statuses": list(old_statuses),
                    },
                )
                order_row = cursor.fetchone()
            connection.commit()
            return order_row is not None

    def cancel_order_with_restock(self, vstitch_order_id, updated_by, old_statuses):
        """Guarded OrderStatus -> 'cancelled' transition (only from one of
        old_statuses, matching OrderStatus.ALLOWED_TRANSITIONS' cancellable
        states) plus restocking exactly this order's line items - same
        two-step shape as PaymentPersistence.mark_payment_failed. Returns
        True if the order was actually cancelled, False if it was already in
        a non-cancellable state (caller treats that as "nothing to do", not
        an error - a double-submitted cancel request is a safe no-op).
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("update_order_status_guarded"),
                    {
                        "new_status": "cancelled",
                        "updated_by": updated_by,
                        "vstitch_order_id": vstitch_order_id,
                        "old_statuses": list(old_statuses),
                    },
                )
                order_row = cursor.fetchone()
                if order_row is not None:
                    cursor.execute(
                        self.query_loader.get_query("restock_variants_for_order"),
                        (vstitch_order_id,),
                    )
            connection.commit()
            return order_row is not None

    def create_return_order(
        self, vstitch_order_id, reason, created_by, shiprocket_return_order_id=None, shiprocket_shipment_id=None
    ):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_return_order"),
                    (vstitch_order_id, shiprocket_return_order_id, shiprocket_shipment_id, reason, created_by),
                )
                vstitch_return_order_id = cursor.fetchone()[0]
            connection.commit()
            return vstitch_return_order_id

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

    def create_razorpay_pending_order(
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
        razorpay_order_id,
    ):
        """Same shape as create_cod_order (order row + stock decrement + order
        items, one transaction) plus the initial VStitch_PaymentTransactions row
        for the Razorpay order that was already created before this call - all
        committed together, so a DB failure here can never leave a Razorpay
        order with no matching VStitch_Orders/transaction row.
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_order_with_status"),
                    (
                        vstitch_user_id,
                        "payment_pending",
                        "razorpay",
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

                cursor.execute(
                    self.query_loader.get_query("insert_payment_transaction"),
                    (
                        vstitch_order_id,
                        razorpay_order_id,
                        total_amount,
                        "INR",
                        created_by_ip_address,
                    ),
                )

            connection.commit()
            return (
                vstitch_order_id,
                order_status,
                payment_method,
                inserted_total_amount,
                remaining_stock_by_variant_id,
            )
