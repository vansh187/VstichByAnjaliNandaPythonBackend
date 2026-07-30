from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchDTO.adminOrderResponseDTO import AdminOrderItemDTO, AdminOrderListResponseDTO, AdminOrderResponseDTO


class AdminOrderService:
    """Business logic for the admin cross-customer order-management endpoints."""

    def __init__(self):
        self.order_persistence = OrderPersistence()

    def list_orders(self, status, payment_method, search, after_id, limit):
        """One page of orders across every customer, newest first, keyset-
        paginated on VstitchOrderId - same shape as the customer-facing
        list_orders_for_user, plus status/payment_method/search filters and
        the placing customer's name/email.
        """
        order_rows = self.order_persistence.list_orders_for_admin(
            status, payment_method, search, after_id, limit + 1
        )
        has_more = len(order_rows) > limit
        page_rows = order_rows[:limit]

        items_by_order_id = self.order_persistence.get_order_items_for_orders_admin(
            [order_row["vstitch_order_id"] for order_row in page_rows]
        )

        orders = [self._to_dto(order_row, items_by_order_id) for order_row in page_rows]
        next_cursor = page_rows[-1]["vstitch_order_id"] if has_more and page_rows else None

        return AdminOrderListResponseDTO(orders=orders, has_more=has_more, next_cursor=next_cursor)

    def get_order(self, vstitch_order_id):
        """Single order across any customer - raises ValueError (-> 404 at
        the API layer) if it doesn't exist."""
        order_row = self.order_persistence.get_order_for_admin(vstitch_order_id)
        if order_row is None:
            raise ValueError(f"Order {vstitch_order_id} was not found.")

        items_by_order_id = self.order_persistence.get_order_items_for_orders_admin([vstitch_order_id])
        return self._to_dto(order_row, items_by_order_id)

    def update_order_status(self, vstitch_order_id, new_status, admin_username):
        """Free-form admin override - any valid OrderStatus from any prior
        status (see update_order_status_admin's comment in
        order_queries.yaml). Raises ValueError if the order doesn't exist.
        """
        was_updated = self.order_persistence.update_order_status_admin(
            vstitch_order_id, new_status, f"admin:{admin_username}"
        )
        if not was_updated:
            raise ValueError(f"Order {vstitch_order_id} was not found.")
        return self.get_order(vstitch_order_id)

    @staticmethod
    def _to_dto(order_row, items_by_order_id):
        return AdminOrderResponseDTO(
            vstitch_order_id=order_row["vstitch_order_id"],
            vstitch_user_id=order_row["vstitch_user_id"],
            customer_name=order_row["customer_name"],
            customer_email=order_row["customer_email"],
            order_status=order_row["order_status"],
            payment_method=order_row["payment_method"],
            total_amount=order_row["total_amount"],
            shipping_recipient_name=order_row["shipping_recipient_name"],
            shipping_address_line1=order_row["shipping_address_line1"],
            shipping_address_line2=order_row["shipping_address_line2"],
            shipping_city=order_row["shipping_city"],
            shipping_state=order_row["shipping_state"],
            shipping_postal_code=order_row["shipping_postal_code"],
            shipping_country=order_row["shipping_country"],
            shipping_phone_number=order_row["shipping_phone_number"],
            awb_code=order_row["awb_code"],
            courier_name=order_row["courier_name"],
            created_date=order_row["created_date"],
            items=[
                AdminOrderItemDTO(
                    vstitch_order_item_id=item["vstitch_order_item_id"],
                    product_name_snapshot=item["product_name_snapshot"],
                    size_snapshot=item["size_snapshot"],
                    color_snapshot=item["color_snapshot"],
                    unit_price_snapshot=item["unit_price_snapshot"],
                    quantity=item["quantity"],
                )
                for item in items_by_order_id.get(order_row["vstitch_order_id"], [])
            ],
        )
