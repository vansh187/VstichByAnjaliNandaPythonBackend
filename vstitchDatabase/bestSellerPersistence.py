from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class BestSellerPersistence:
    """Database logic ranking products by sales, against VStitch_Orders/OrderItems."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("best_seller_queries.yaml")

    def get_top_selling_product_ids(self, since_date, exclude_ids, limit):
        """Returns product ids ranked by units sold (desc), already excluding
        `exclude_ids` and anything not currently buyable. `since_date=None`
        means all-time."""
        if limit <= 0:
            return []
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_top_selling_product_ids"),
                    {
                        "since_date": since_date,
                        "exclude_ids": list(exclude_ids),
                        "limit": limit,
                    },
                )
                return [row[0] for row in cursor.fetchall()]

    def get_newest_active_product_ids(self, exclude_ids, limit):
        if limit <= 0:
            return []
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("get_newest_active_product_ids"),
                    {
                        "exclude_ids": list(exclude_ids),
                        "limit": limit,
                    },
                )
                return [row[0] for row in cursor.fetchall()]
