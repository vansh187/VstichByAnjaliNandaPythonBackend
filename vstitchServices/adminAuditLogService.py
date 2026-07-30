import logging

from vstitchDatabase.adminAuditLogPersistence import AdminAuditLogPersistence
from vstitchDTO.adminAuditLogResponseDTO import AdminAuditLogEntryDTO, AdminAuditLogListResponseDTO

logger = logging.getLogger(__name__)


class AdminAuditLogService:
    """Records what an admin changed, for incident response and catching a
    misbehaving/compromised admin account. Deliberately never raises: a
    logging hiccup (DB blip, table not yet migrated in some environment)
    must never break the actual admin action it's recording - the mutation
    itself has already succeeded by the time record() is called.
    """

    def __init__(self):
        self.admin_audit_log_persistence = AdminAuditLogPersistence()

    def record(self, vstitch_admin_id, action_type, resource_type, resource_id, details=None):
        try:
            self.admin_audit_log_persistence.insert_audit_log_entry(
                vstitch_admin_id, action_type, resource_type, resource_id, details
            )
        except Exception:
            logger.exception(
                "Failed to record admin audit log entry (admin_id=%s, action_type=%s, resource_type=%s, "
                "resource_id=%s) - the action itself already succeeded and was not affected.",
                vstitch_admin_id,
                action_type,
                resource_type,
                resource_id,
            )

    def list_entries(self, admin_id, action_type, after_id, limit):
        """Keyset-paginated, newest first - same shape/convention as every
        other admin list endpoint (see list_orders_for_admin)."""
        rows = self.admin_audit_log_persistence.list_audit_log_entries(admin_id, action_type, after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        entries = [AdminAuditLogEntryDTO(**row) for row in page_rows]
        next_cursor = page_rows[-1]["vstitch_admin_audit_log_id"] if has_more and page_rows else None
        return AdminAuditLogListResponseDTO(entries=entries, next_cursor=next_cursor, has_more=has_more)


admin_audit_log_service = AdminAuditLogService()
