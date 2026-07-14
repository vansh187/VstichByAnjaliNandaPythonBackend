from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class SignupPersistence:
    """Database logic backing the signup flow against VStitch_Users."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("user_queries.yaml")

    def is_username_taken(self, vstitch_user_name):
        connection = self.connection_factory.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_username_exists"), (vstitch_user_name,))
                return cursor.fetchone() is not None
        finally:
            self.connection_factory.release_connection(connection)

    def is_email_taken(self, email):
        connection = self.connection_factory.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_email_exists"), (email,))
                return cursor.fetchone() is not None
        finally:
            self.connection_factory.release_connection(connection)

    def is_phone_number_taken(self, phone_number):
        connection = self.connection_factory.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_phone_exists"), (phone_number,))
                return cursor.fetchone() is not None
        finally:
            self.connection_factory.release_connection(connection)

    def create_user(
        self,
        vstitch_user_name,
        hashed_password,
        first_name,
        last_name,
        email,
        phone_number,
        created_by_ip_address,
    ):
        connection = self.connection_factory.get_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_user"),
                    (
                        vstitch_user_name,
                        hashed_password,
                        first_name,
                        last_name,
                        email,
                        phone_number,
                        created_by_ip_address,
                    ),
                )
                inserted_row = cursor.fetchone()
            connection.commit()
            return inserted_row
        except Exception:
            connection.rollback()
            raise
        finally:
            self.connection_factory.release_connection(connection)
