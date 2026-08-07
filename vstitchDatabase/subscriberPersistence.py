from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class SubscriberPersistence:
    """Database logic backing VSTITCH_SUBSCRIBERS - the newsletter
    "Subscribe" form's mailing list."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("subscriber_queries.yaml")

    def save_subscriber(self, email, created_by, updated_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_subscriber"),
                    {"email": email, "created_by": created_by, "updated_by": updated_by},
                )
                vstitch_subscriber_id, email, created_date, updated_date = cursor.fetchone()
            connection.commit()
            return {
                "vstitch_subscriber_id": vstitch_subscriber_id,
                "email": email,
                "created_date": created_date,
                "updated_date": updated_date,
            }
