from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchDTO.orderResponseDTO import CreateOrderResponseDTO, OrderItemResponseDTO


class OrderService:
    """Business logic for placing a cash-on-delivery order."""

    def __init__(self):
        self.order_persistence = OrderPersistence()

    def place_cod_order(self, create_order_request_dto, vstitch_user_id, created_by_ip_address):
        # Merge repeated variants into one line up front: it collapses the request
        # to one row per variant (matching the persistence layer's batched, one
        # row per variant stock decrement) and keeps a single order-item row per
        # variant instead of splitting one product across duplicate lines.
        requested_quantity_by_variant_id = {}
        for requested_item in create_order_request_dto.items:
            variant_id = requested_item.vstitch_product_variant_id
            requested_quantity_by_variant_id[variant_id] = (
                requested_quantity_by_variant_id.get(variant_id, 0) + requested_item.quantity
            )

        variants_by_id = self.order_persistence.get_variants_for_order(
            list(requested_quantity_by_variant_id.keys())
        )

        order_items = []
        total_amount = 0

        for variant_id, quantity in requested_quantity_by_variant_id.items():
            variant = variants_by_id.get(variant_id)
            if variant is None or not variant["is_active"]:
                raise ValueError(f"Product variant {variant_id} is not available.")
            if quantity > variant["stock_quantity"]:
                raise ValueError(
                    f"Insufficient stock for {variant['product_name']} "
                    f"({variant['size']}/{variant['color']})."
                )

            line_total = variant["price"] * quantity
            total_amount += line_total

            order_items.append(
                {
                    "vstitch_product_variant_id": variant_id,
                    "product_name_snapshot": variant["product_name"],
                    "size_snapshot": variant["size"],
                    "color_snapshot": variant["color"],
                    "unit_price_snapshot": variant["price"],
                    "quantity": quantity,
                    "line_total": line_total,
                }
            )

        vstitch_order_id, order_status, payment_method, inserted_total_amount = (
            self.order_persistence.create_cod_order(
                vstitch_user_id,
                total_amount,
                create_order_request_dto.shipping_recipient_name,
                create_order_request_dto.shipping_address_line1,
                create_order_request_dto.shipping_address_line2,
                create_order_request_dto.shipping_city,
                create_order_request_dto.shipping_state,
                create_order_request_dto.shipping_postal_code,
                create_order_request_dto.shipping_country,
                create_order_request_dto.shipping_phone_number,
                created_by_ip_address,
                order_items,
            )
        )

        return CreateOrderResponseDTO(
            vstitch_order_id=vstitch_order_id,
            order_status=order_status,
            payment_method=payment_method,
            total_amount=inserted_total_amount,
            items=[
                OrderItemResponseDTO(
                    vstitch_product_variant_id=item["vstitch_product_variant_id"],
                    product_name=item["product_name_snapshot"],
                    size=item["size_snapshot"],
                    color=item["color_snapshot"],
                    unit_price=item["unit_price_snapshot"],
                    quantity=item["quantity"],
                    line_total=item["line_total"],
                )
                for item in order_items
            ],
            message="Order placed successfully. Pay cash on delivery.",
        )
