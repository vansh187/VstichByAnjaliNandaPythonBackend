"""One-off provisioning script: creates a VStitch_AdminUsers row.

There is no self-serve admin-signup endpoint (deliberately - exposing one
would make a privileged account creatable from the public internet). This
script is the only way to create an admin account: it hashes the password
the same way the app does (PasswordHashService) and inserts the row
directly. Run it once per admin you need to provision.

Usage:
    python scripts/create_admin_user.py <admin_username> <email> <password>
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vstitchServices.passwordHashService import PasswordHashService  # noqa: E402

load_dotenv()

CREATED_BY = "provisioning-script"


def main():
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <admin_username> <email> <password>")
        sys.exit(1)

    admin_username, email, password = sys.argv[1], sys.argv[2], sys.argv[3]
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    hashed_password = PasswordHashService().hash_password(password)

    connection = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO VStitch_AdminUsers (AdminUsername, AdminPassword, Email, created_by, created_date)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING VstitchAdminId, AdminUsername, Email, created_date;
                """,
                (admin_username, hashed_password, email, CREATED_BY),
            )
            row = cursor.fetchone()
        connection.commit()
    except psycopg2.errors.UniqueViolation:
        connection.rollback()
        print(f"An admin with username '{admin_username}' or email '{email}' already exists.")
        sys.exit(1)
    finally:
        connection.close()

    print(f"Created admin user: id={row[0]} username={row[1]} email={row[2]} created={row[3]}")


if __name__ == "__main__":
    main()
