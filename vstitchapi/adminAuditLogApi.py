from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from vstitchDTO.adminAuditLogResponseDTO import AdminAuditLogListResponseDTO
from vstitchServices.adminAuditLogService import admin_audit_log_service
from vstitchServices.adminAuthDependency import get_current_admin


class AdminAuditLogApi:
    """Exposes GET /admin/audit-log - otherwise the audit trail every other
    admin mutation writes to would be write-only and no one could actually
    see it. Admin-JWT-gated at the router level, same mechanism as every
    other admin router.
    """

    def __init__(self):
        self.router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
        self.router.add_api_route(
            "/audit-log",
            self.list_audit_log,
            methods=["GET"],
            response_model=AdminAuditLogListResponseDTO,
        )

    def list_audit_log(
        self,
        admin_id: Optional[int] = Query(default=None, ge=1),
        action_type: Optional[str] = Query(default=None, max_length=100),
        after_id: Optional[int] = Query(default=None, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        try:
            return admin_audit_log_service.list_entries(admin_id, action_type, after_id, limit)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Something went wrong while loading the audit log. Please try again later.",
            )


admin_audit_log_api = AdminAuditLogApi()
admin_audit_log_router = admin_audit_log_api.router
