import psycopg2.errors

from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader
from vstitchDatabase.uniqueConstraintError import UniqueConstraintError

# Constraint/index names from vstitch_categories.sql - translated into a
# human-readable ValueError message when INSERT/UPDATE hits either one.
CATEGORY_UNIQUE_CONSTRAINT_MESSAGES = {
    "uq_categories_name_parent": "A category with this name already exists under the same parent.",
    "uq_categories_name_top_level": "A top-level category with this name already exists.",
}

ADMIN_CATEGORY_COLUMNS = ("vstitch_category_id", "category_name", "parent_category_id", "image_url", "is_active")


class CategoryPersistence:
    """Database logic backing catalog navigation against VStitch_Categories."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("category_queries.yaml")

    def list_active_categories(self):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("list_active_categories"))
                rows = cursor.fetchall()
            column_names = ("vstitch_category_id", "category_name", "parent_category_id", "image_url")
            return [dict(zip(column_names, row)) for row in rows]

    # --- Admin: category management ---------------------------------------

    def list_all_categories_admin(self):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("list_all_categories_admin"))
                rows = cursor.fetchall()
            return [dict(zip(ADMIN_CATEGORY_COLUMNS, row)) for row in rows]

    def get_category_for_admin(self, vstitch_category_id):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("get_category_by_id_admin"), (vstitch_category_id,))
                row = cursor.fetchone()
            return dict(zip(ADMIN_CATEGORY_COLUMNS, row)) if row is not None else None

    def insert_category(self, category_name, parent_category_id, image_url, created_by):
        """Raises ValueError (not a raw psycopg2 exception) on a name
        collision - see the race-safe-uniqueness note in
        ADMIN_API_CONTRACT.md's implementation plan: attempt the INSERT,
        translate a UniqueViolation via its constraint/index name, rather
        than a check-then-insert pre-check that a concurrent request could
        still race past.
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("insert_category"),
                        {
                            "category_name": category_name,
                            "parent_category_id": parent_category_id,
                            "image_url": image_url,
                            "created_by": created_by,
                        },
                    )
                except psycopg2.errors.UniqueViolation as unique_violation:
                    connection.rollback()
                    raise UniqueConstraintError(
                        self._translate_unique_violation(unique_violation)
                    ) from unique_violation
                row = cursor.fetchone()
            connection.commit()
            return dict(zip(ADMIN_CATEGORY_COLUMNS, row))

    def update_category(self, vstitch_category_id, category_name, parent_category_id, image_url, is_active, updated_by):
        """Full-row update - see update_category's comment in
        category_queries.yaml. Returns None if the category doesn't exist,
        raises ValueError on a name collision (same translation as insert).
        """
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        self.query_loader.get_query("update_category"),
                        {
                            "vstitch_category_id": vstitch_category_id,
                            "category_name": category_name,
                            "parent_category_id": parent_category_id,
                            "image_url": image_url,
                            "is_active": is_active,
                            "updated_by": updated_by,
                        },
                    )
                except psycopg2.errors.UniqueViolation as unique_violation:
                    connection.rollback()
                    raise UniqueConstraintError(
                        self._translate_unique_violation(unique_violation)
                    ) from unique_violation
                row = cursor.fetchone()
            connection.commit()
            return dict(zip(ADMIN_CATEGORY_COLUMNS, row)) if row is not None else None

    def soft_delete_category(self, vstitch_category_id, updated_by):
        """Sets IsActive=FALSE - never a real DELETE, see soft_delete_category's
        comment in category_queries.yaml. Returns True if the category
        existed and was deactivated."""
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("soft_delete_category"),
                    {"vstitch_category_id": vstitch_category_id, "updated_by": updated_by},
                )
                row = cursor.fetchone()
            connection.commit()
            return row is not None

    @staticmethod
    def _translate_unique_violation(unique_violation):
        constraint_name = getattr(unique_violation.diag, "constraint_name", None)
        return CATEGORY_UNIQUE_CONSTRAINT_MESSAGES.get(
            constraint_name, "A category with conflicting details already exists."
        )
