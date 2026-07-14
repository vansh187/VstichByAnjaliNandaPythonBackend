import bcrypt


class PasswordHashService:
    """Hashes and verifies passwords with bcrypt so they are never stored in plaintext.

    Uses the bcrypt library directly rather than passlib: passlib 1.7.4's version
    probing reads bcrypt's removed `__about__` module and silently breaks its own
    72-byte length check against bcrypt>=4.1, rejecting even short passwords.
    """

    def __init__(self):
        self.bcrypt_rounds = 12

    def hash_password(self, plain_text_password):
        password_bytes = plain_text_password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def verify_password(self, plain_text_password, hashed_password):
        try:
            return bcrypt.checkpw(plain_text_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:
            return False
