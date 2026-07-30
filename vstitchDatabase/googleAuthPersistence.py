from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader

USER_COLUMNS = ("vstitch_user_id", "vstitch_user_name", "first_name", "last_name", "email", "google_id", "auth_provider")


class GoogleAuthPersistence:
    """Database logic backing Google OAuth login against VStitch_Users."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("user_queries.yaml")

    def get_user_by_google_id(self, google_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_user_by_google_id"), (google_id,))
                user_row = cursor.fetchone()
            return dict(zip(USER_COLUMNS, user_row)) if user_row is not None else None

    def get_user_by_email(self, email):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_user_by_email"), (email,))
                user_row = cursor.fetchone()
            return dict(zip(USER_COLUMNS, user_row)) if user_row is not None else None

    def is_username_taken(self, vstitch_user_name):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("check_username_exists"), (vstitch_user_name,))
                return cursor.fetchone() is not None

    def link_google_id_to_user(self, vstitch_user_id, google_id, updated_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("link_google_id_to_user"),
                    {"vstitch_user_id": vstitch_user_id, "google_id": google_id, "updated_by": updated_by},
                )
                row = cursor.fetchone()
            connection.commit()
            vstitch_user_id, vstitch_user_name, email = row
            return {"vstitch_user_id": vstitch_user_id, "vstitch_user_name": vstitch_user_name, "email": email}

    def create_google_user(self, vstitch_user_name, first_name, last_name, email, google_id, created_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_google_user"),
                    (vstitch_user_name, first_name, last_name, email, google_id, created_by),
                )
                row = cursor.fetchone()
            connection.commit()
            vstitch_user_id, vstitch_user_name, email = row
            return {"vstitch_user_id": vstitch_user_id, "vstitch_user_name": vstitch_user_name, "email": email}
