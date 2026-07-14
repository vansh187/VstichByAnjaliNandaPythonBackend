from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class SchemaPersistence:
    """Ensures the VStitch_Users table exists before the app starts serving traffic."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("user_queries.yaml")

    def create_users_table_if_not_exists(self):
        connection = self.connection_factory.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("create_table"))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self.connection_factory.release_connection(connection)
