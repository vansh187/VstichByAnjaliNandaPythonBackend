-- Migration: adds real revocation for admin JWTs. A stateless JWT can't be
-- killed early by itself - if one leaks (stolen laptop, an XSS bug in a
-- badly-built frontend), it stays valid for its full lifetime with no way
-- to stop it. TokenValidAfterUtc gives a floor: any token whose "iat"
-- (issued-at) claim is older than this timestamp is rejected, even if its
-- signature and expiry are still otherwise valid.
--
-- Nullable = no restriction, so every token issued before this migration
-- runs keeps working immediately after it runs (NULL never fails the
-- iat < token_valid_after_utc check in adminAuthDependency.get_current_admin).
--
-- Run once, directly against Supabase (matches how 0004/0006/0007 were
-- applied - see README "Database schema"). Also mirrored into
-- admin_queries.yaml's create_admin_users_table, since VStitch_AdminUsers is
-- foundational infra applied at app boot the same way it already is.

ALTER TABLE VStitch_AdminUsers
    ADD COLUMN IF NOT EXISTS TokenValidAfterUtc TIMESTAMP;
