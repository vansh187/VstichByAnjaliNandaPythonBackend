from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader

REVIEW_COLUMNS = ("vstitch_review_id", "vstitch_product_id", "rating", "review_text", "created_date", "updated_date")
REVIEW_LIST_ITEM_COLUMNS = ("vstitch_review_id", "reviewer_name", "rating", "review_text", "created_date")


class ReviewPersistence:
    """Database logic backing the product-review read/write paths."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("review_queries.yaml")

    def product_exists(self, vstitch_product_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_product_exists"), (vstitch_product_id,))
                return cursor.fetchone() is not None

    def upsert_review(self, vstitch_user_id, vstitch_product_id, rating, review_text, actor):
        """Insert-or-update in one atomic statement - see upsert_review's
        comment in review_queries.yaml. Returns (review_dict, was_created)."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("upsert_review"),
                    {
                        "vstitch_user_id": vstitch_user_id,
                        "vstitch_product_id": vstitch_product_id,
                        "rating": rating,
                        "review_text": review_text,
                        "actor": actor,
                    },
                )
                row = cursor.fetchone()
            connection.commit()
            was_created = row[-1]
            return dict(zip(REVIEW_COLUMNS, row[:-1])), was_created

    def get_review_stats_for_product(self, vstitch_product_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_review_stats_for_product"), (vstitch_product_id,))
                average_rating, review_count = cursor.fetchone()
            return (float(average_rating) if average_rating is not None else None), review_count

    def list_reviews_for_product(self, vstitch_product_id, before_id, limit_plus_one):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("list_reviews_for_product"),
                    {
                        "vstitch_product_id": vstitch_product_id,
                        "before_id": before_id,
                        "limit_plus_one": limit_plus_one,
                    },
                )
                rows = cursor.fetchall()
            return [dict(zip(REVIEW_LIST_ITEM_COLUMNS, row)) for row in rows]
