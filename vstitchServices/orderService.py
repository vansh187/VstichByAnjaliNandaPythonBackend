from vstitchDatabase.orderPersistence import OrderPersistence
from vstitchDTO.orderResponseDTO import CreateOrderResponseDTO, OrderItemResponseDTO
from vstitchServices.localCacheService import local_cache_service


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
                    "vstitch_product_id": variant["vstitch_product_id"],
                    "product_name_snapshot": variant["product_name"],
                    "size_snapshot": variant["size"],
                    "color_snapshot": variant["color"],
                    "unit_price_snapshot": variant["price"],
                    "quantity": quantity,
                    "line_total": line_total,
                }
            )

        vstitch_order_id, order_status, payment_method, inserted_total_amount, remaining_stock_by_variant_id = (
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

        self._evict_sold_out_products_from_cache(order_items, remaining_stock_by_variant_id)

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

    def _evict_sold_out_products_from_cache(self, order_items, remaining_stock_by_variant_id):
        """If this order took a variant's stock to 0, don't leave the catalog
        cache showing it as in stock for the rest of its TTL - evict it now so
        the next browse/detail request sees the sellout immediately instead of
        potentially inviting another order that's already destined for a 409.
        Called after the order transaction has committed, so it only runs once
        the sellout is real, never speculatively.
        """
        sold_out_product_ids = {
            order_item["vstitch_product_id"]
            for order_item in order_items
            if remaining_stock_by_variant_id.get(order_item["vstitch_product_variant_id"]) == 0
        }
        if not sold_out_product_ids:
            return

        for product_id in sold_out_product_ids:
            local_cache_service.delete(f"products:detail:{product_id}")
        # A sold-out product can appear in any number of cached listing pages
        # (different category/search/pagination combinations) - there's no
        # cheap way to know which ones without an inverted index, so clear all
        # of them. Cheap to rebuild (catalog is small) and correctness here
        # matters more than preserving unrelated list cache entries.
        local_cache_service.clear_prefix("products:list:")
