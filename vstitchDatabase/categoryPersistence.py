from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class CategoryPersistence:
    """Database logic backing catalog navigation against VStitch_Categories."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("category_queries.yaml")

    def list_active_categories(self):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("list_active_categories"))
                rows = cursor.fetchall()
            column_names = ("vstitch_category_id", "category_name", "parent_category_id", "image_url")
            return [dict(zip(column_names, row)) for row in rows]
