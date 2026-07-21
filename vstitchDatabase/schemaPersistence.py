from vstitchDatabase.adminAuditLogPersistence import AdminAuditLogPersistence
from vstitchDatabase.ConnectionFactory import connection_factory
from vstitchDatabase.queryLoader import QueryLoader


class SchemaPersistence:
    """Ensures the VStitch_Users / VStitch_AdminUsers / VStitch_AdminAuditLog
    tables exist before the app starts serving traffic - all three are
    foundational auth/security infra the app shouldn't depend on a manual
    migration having been run first, unlike every other table (products,
    orders, ...), which is applied via a one-off manual migration instead."""

    def __init__(self):
        self.connection_factory = connection_factory
        self.query_loader = QueryLoader("user_queries.yaml")
        self.admin_query_loader = QueryLoader("admin_queries.yaml")
        self.admin_audit_log_persistence = AdminAuditLogPersistence()

    def create_users_table_if_not_exists(self):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.query_loader.get_query("create_table"))
            connection.commit()

    def create_admin_users_table_if_not_exists(self):
        with self.connection_factory.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.admin_query_loader.get_query("create_admin_users_table"))
            connection.commit()

    def create_admin_audit_log_table_if_not_exists(self):
        self.admin_audit_log_persistence.create_table_if_not_exists()
