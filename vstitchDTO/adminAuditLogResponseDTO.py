from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class AdminAuditLogEntryDTO(BaseModel):
    vstitch_admin_audit_log_id: int
    vstitch_admin_id: int
    admin_username: str
    action_type: str
    resource_type: str
    resource_id: Optional[int]
    details: Optional[Any]
    created_date: datetime


class AdminAuditLogListResponseDTO(BaseModel):
    entries: List[AdminAuditLogEntryDTO]
    next_cursor: Optional[int]
    has_more: bool
