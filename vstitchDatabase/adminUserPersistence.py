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

    def get_admin_by_id(self, vstitch_admin_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_admin_by_id"), (vstitch_admin_id,))
                admin_row = cursor.fetchone()
            if admin_row is None:
                return None
            column_names = ("vstitch_admin_id", "admin_username", "email", "is_active", "token_valid_after_utc")
            return dict(zip(column_names, admin_row))

    def revoke_all_sessions(self, vstitch_admin_id, updated_by):
        """Sets TokenValidAfterUtc to now - every access token issued to
        this admin before this call now fails get_current_admin's iat check,
        even though it hasn't expired yet. Returns True if the admin existed."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("revoke_all_sessions"),
                    {"vstitch_admin_id": vstitch_admin_id, "updated_by": updated_by},
                )
                row = cursor.fetchone()
            connection.commit()
            return row is not None
