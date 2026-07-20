-- VStitch_AdminUsers: authentication table for admin-panel staff, kept
-- separate from VStitch_Users (customers) rather than a role column on it -
-- admin and customer principals have different lifecycle/security needs
-- (password rotation, 2FA later) and a separate table means an admin JWT can
-- never be satisfied by a customer login or vice versa.
-- Engine: PostgreSQL (psycopg2). AdminPassword stores a bcrypt hash (same
-- PasswordHashService as customer signup); admin JWTs are issued separately
-- using ADMIN_JWT_SECRET / ADMIN_JWT_ALGORITHM (HS256) from .env after
-- successful login. No self-serve signup endpoint exists for this table -
-- rows are created via a one-off provisioning script.

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
