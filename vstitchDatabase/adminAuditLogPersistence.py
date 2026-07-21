import json

from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader

AUDIT_LOG_COLUMNS = (
    "vstitch_admin_audit_log_id",
    "vstitch_admin_id",
    "admin_username",
    "action_type",
    "resource_type",
    "resource_id",
    "details",
    "created_date",
)


class AdminAuditLogPersistence:
    """Database logic backing the admin audit-log write/read paths."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("admin_audit_log_queries.yaml")

    def create_table_if_not_exists(self):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("create_table"))
            connection.commit()

    def insert_audit_log_entry(self, vstitch_admin_id, action_type, resource_type, resource_id, details):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("insert_audit_log_entry"),
                    {
                        "vstitch_admin_id": vstitch_admin_id,
                        "action_type": action_type,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "details": json.dumps(details) if details is not None else None,
                    },
                )
                row = cursor.fetchone()
            connection.commit()
            return row[0]

    def list_audit_log_entries(self, admin_id, action_type, after_id, limit_plus_one):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    self.query_loader.get_query("list_audit_log_entries"),
                    {
                        "admin_id": admin_id,
                        "action_type": action_type,
                        "after_id": after_id,
                        "limit_plus_one": limit_plus_one,
                    },
                )
                rows = cursor.fetchall()
            return [dict(zip(AUDIT_LOG_COLUMNS, row)) for row in rows]
