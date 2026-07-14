from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class LoginPersistence:
    """Database logic backing the login flow against VStitch_Users."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("user_queries.yaml")

    def get_user_by_username(self, vstitch_user_name):
        connection = self.connection_factory.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_user_by_username"), (vstitch_user_name,))
                user_row = cursor.fetchone()
            if user_row is None:
                return None
            column_names = (
                "vstitch_user_id",
                "vstitch_user_name",
                "vstitch_password",
                "first_name",
                "last_name",
                "email",
                "phone_number",
            )
            return dict(zip(column_names, user_row))
        finally:
            self.connection_factory.release_connection(connection)
