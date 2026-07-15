from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class SignupPersistence:
    """Database logic backing the signup flow against VStitch_Users."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("user_queries.yaml")

    def is_username_taken(self, vstitch_user_name):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_username_exists"), (vstitch_user_name,))
                return cursor.fetchone() is not None

    def is_email_taken(self, email):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_email_exists"), (email,))
                return cursor.fetchone() is not None

    def is_phone_number_taken(self, phone_number):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_phone_exists"), (phone_number,))
                return cursor.fetchone() is not None

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
        with self.connection_factory.connection() as connection:
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
