-- Migration: introduces the admin-panel API surface's identity table.
-- VStitch_Users has no role/scope column and the customer JWT carries no
-- role claim, so there is nothing today that distinguishes an admin caller
-- from a customer - internalOpsAuthDependency.py's shared ops key was an
-- explicit stopgap pending "real admin-role auth once one exists". This is
-- that table. Kept separate from VStitch_Users rather than adding a role
-- column to it - see vstitch_admin_users.sql's header comment for why.
--
-- Run once, directly against Supabase (matches how the rest of the schema
-- is applied - see README "Database schema"). Also mirrored into
-- SchemaPersistence.create_admin_users_table_if_not_exists(), called at
-- app boot the same way VStitch_Users already is, since admin auth is
-- foundational infra the app shouldn't depend on a manual migration step
-- having been run first.

CREATE TABLE IF NOT EXISTS VStitch_AdminUsers (
    VstitchAdminId    BIGSERIAL     PRIMARY KEY,
    AdminUsername     VARCHAR(250)  NOT NULL,
    AdminPassword     VARCHAR(250)  NOT NULL,
    Email             VARCHAR(250)  NOT NULL,
    IsActive          BOOLEAN       NOT NULL DEFAULT TRUE,
    created_by        VARCHAR(250)  NOT NULL,
    created_date      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by        VARCHAR(250),
    updated_date      TIMESTAMP,

    CONSTRAINT uq_admin_users_username UNIQUE (AdminUsername),
    CONSTRAINT uq_admin_users_email UNIQUE (Email)
);
