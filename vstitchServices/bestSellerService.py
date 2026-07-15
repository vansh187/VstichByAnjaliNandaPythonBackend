from datetime import datetime, timedelta, timezone

from vstitchDatabase.bestSellerPersistence import BestSellerPersistence
from vstitchDatabase.productPersistence import ProductPersistence
from vstitchDTO.bestSellersResponseDTO import BestSellerItemDTO, BestSellersResponseDTO
from vstitchServices.localCacheService import local_cache_service

RECENT_WINDOW_DAYS = 30
CACHE_TTL_SECONDS = 600


class BestSellerService:
    """Ranks products by sales for the storefront's Best Sellers section.

    Three-tier fallback so the section is always full on a young catalog
    without ever mislabeling padding as real demand:
      1. Units sold in the last 30 days (source="sales").
      2. If that doesn't fill `limit`, units sold all-time (source="sales").
      3. If sales still don't fill `limit`, newest active products
         (source="fallback") - padding, not a sales signal.
    Each tier only fills the gap the previous one left; a product picked in
    an earlier tier is never picked again later.
    """

    def __init__(self):
        self.best_seller_persistence = BestSellerPersistence()
        self.product_persistence = ProductPersistence()

    def list_best_sellers(self, limit):
        cache_key = f"best_sellers:{limit}"
        cached_response = local_cache_service.get(cache_key)
        if cached_response is not None:
            return cached_response

        ranked = []  # list of (vstitch_product_id, source)
        picked_ids = set()

        since_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=RECENT_WINDOW_DAYS)
        for product_id in self.best_seller_persistence.get_top_selling_product_ids(since_date, picked_ids, limit):
            ranked.append((product_id, "sales"))
            picked_ids.add(product_id)

        remaining = limit - len(ranked)
        if remaining > 0:
            for product_id in self.best_seller_persistence.get_top_selling_product_ids(
                None, picked_ids, remaining
            ):
                ranked.append((product_id, "sales"))
                picked_ids.add(product_id)

        remaining = limit - len(ranked)
        if remaining > 0:
            for product_id in self.best_seller_persistence.get_newest_active_product_ids(picked_ids, remaining):
                ranked.append((product_id, "fallback"))
                picked_ids.add(product_id)

        products_by_id = self.product_persistence.get_products_by_ids([product_id for product_id, _ in ranked])

        items = []
        qualifying_count = 0
        for product_id, source in ranked:
            product = products_by_id.get(product_id)
            if product is None:
                # Ranked a moment ago but no longer buyable by the time the
                # card data was fetched (e.g. deactivated in between) - skip
                # it rather than fail the whole response; the section just
                # renders one item short of `limit` this time.
                continue

            items.append(
                BestSellerItemDTO(
                    vstitch_product_id=product["vstitch_product_id"],
                    product_name=product["product_name"],
                    category_id=product["vstitch_category_id"],
                    category_name=product["category_name"],
                    min_price=product["min_price"],
                    max_price=product["max_price"],
                    primary_image_url=product["image_url"],
                    available_colors=product["colors"] or [],
                    in_stock=bool(product["in_stock"]),
                    source=source,
                )
            )
            if source == "sales":
                qualifying_count += 1

        response = BestSellersResponseDTO(items=items, qualifying_count=qualifying_count)
        local_cache_service.set(cache_key, response, CACHE_TTL_SECONDS)
        return response
