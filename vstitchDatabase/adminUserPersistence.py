from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class AdminUserPersistence:
    """Database logic backing the admin login flow against VStitch_AdminUsers."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("admin_queries.yaml")

    def get_admin_by_username(self, admin_username):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_admin_by_username"), (admin_username,))
                admin_row = cursor.fetchone()
            if admin_row is None:
                return None
            column_names = ("vstitch_admin_id", "admin_username", "admin_password", "email", "is_active")
            return dict(zip(column_names, admin_row))
