-- Migration: introduces a queryable trail of what an admin actually changed.
-- updated_by/updated_date columns already exist per-row across the admin
-- surface, but there was no single place to answer "what has admin X done"
-- or "who touched resource Y and when" without diffing row history by hand.
-- Useful both for incident response (a leaked/compromised admin token) and
-- for catching a misbehaving admin account.
--
-- Details is JSONB rather than a fixed set of columns - the fields worth
-- recording differ per action type (a status change vs. a product create),
-- and this table's only job is "what happened," not enforcing structure on
-- it.
--
-- Run once, directly against Supabase (matches how 0004/0006/0007/0008 were
-- applied - see README "Database schema"). Also mirrored into
-- SchemaPersistence via admin_audit_log_queries.yaml's create_table, applied
-- at app boot the same way VStitch_AdminUsers already is.

CREATE TABLE IF NOT EXISTS VStitch_AdminAuditLog (
    VstitchAdminAuditLogId  BIGSERIAL     PRIMARY KEY,
    VstitchAdminId          BIGINT        NOT NULL REFERENCES VStitch_AdminUsers(VstitchAdminId),
    ActionType              VARCHAR(100)  NOT NULL,
    ResourceType            VARCHAR(100)  NOT NULL,
    ResourceId              BIGINT,
    Details                 JSONB,
    created_date            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_admin_id ON VStitch_AdminAuditLog (VstitchAdminId);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_created_date ON VStitch_AdminAuditLog (created_date);
