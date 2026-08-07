from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader

USER_COLUMNS = ("vstitch_user_id", "vstitch_user_name", "first_name", "last_name", "email", "google_id", "auth_provider")
OTP_COLUMNS = ("otp_hash", "expires_at", "consumed_at", "attempt_count", "updated_date")


class PasswordResetPersistence:
    """Database logic backing the "Forgot password?" email-OTP flow:
    VSTITCH_PASSWORD_RESET_OTPS plus the one VStitch_Users password-update
    query it needs."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("password_reset_queries.yaml")
        self.user_query_loader = QueryLoader("user_queries.yaml")

    def get_user_by_email(self, email):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.user_query_loader.get_query("get_user_by_email"), (email,))
                user_row = cursor.fetchone()
            return dict(zip(USER_COLUMNS, user_row)) if user_row is not None else None

    def save_otp(self, vstitch_user_id, otp_hash, expires_at, created_by):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("upsert_otp"),
                    {
                        "vstitch_user_id": vstitch_user_id,
                        "otp_hash": otp_hash,
                        "expires_at": expires_at,
                        "created_by": created_by,
                    },
                )
            connection.commit()

    def get_otp_for_user(self, vstitch_user_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_otp_for_user"), (vstitch_user_id,))
                otp_row = cursor.fetchone()
            return dict(zip(OTP_COLUMNS, otp_row)) if otp_row is not None else None

    def increment_attempt_count(self, vstitch_user_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("increment_otp_attempt_count"), (vstitch_user_id,))
                new_attempt_count = cursor.fetchone()[0]
            connection.commit()
            return new_attempt_count

    def finalize_password_reset(self, vstitch_user_id, new_password_hash, updated_by):
        """Updates the password and consumes the OTP in one transaction -
        deliberately not two separate calls (each with its own commit):
        if the password update succeeded but consuming the OTP failed
        (e.g. a transient DB error) with those as separate commits, the OTP
        row would be left ConsumedAt=NULL and still within its expiry
        window, replayable via /confirm to set the password again even
        though the caller already saw a 500. Committing them together
        means either both happen or neither does."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.user_query_loader.get_query("update_password_by_user_id"),
                    {
                        "vstitch_user_id": vstitch_user_id,
                        "new_password_hash": new_password_hash,
                        "updated_by": updated_by,
                    },
                )
                cursor.execute(
                    self.query_loader.get_query("consume_otp"),
                    {"vstitch_user_id": vstitch_user_id, "updated_by": updated_by},
                )
            connection.commit()
