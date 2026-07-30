-- VStitch_Users: signup/authentication table for the VStitch ecommerce backend.
-- Engine: PostgreSQL (psycopg2 / SQLAlchemy per requirements.txt).
-- VstitchPassword stores a bcrypt hash (via passlib); JWTs are issued separately
-- using JWT_SECRET / JWT_ALGORITHM (HS256) from .env after successful login.
--
-- Also backs Google OAuth login (see migrations/0007_add_google_oauth_login.sql):
-- GoogleId is Google's stable `sub` claim, AuthProvider is 'local' or 'google'.
-- VstitchPassword/PhoneNumber are nullable because a Google-only account never
-- collects either.

CREATE TABLE IF NOT EXISTS VStitch_Users (
    VstitchUserId    BIGSERIAL     PRIMARY KEY,
    VstitchUserName  VARCHAR(250)  NOT NULL,
    VstitchPassword  VARCHAR(250),
    FirstName        VARCHAR(250)  NOT NULL,
    LastName         VARCHAR(250)  NOT NULL,
    Email            VARCHAR(250)  NOT NULL,
    PhoneNumber      VARCHAR(250),
    GoogleId         VARCHAR(250),
    AuthProvider     VARCHAR(20)   NOT NULL DEFAULT 'local',
    created_by       VARCHAR(250)  NOT NULL,
    created_date     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by       VARCHAR(250),
    updated_date     TIMESTAMP,

    CONSTRAINT uq_vstitch_users_username UNIQUE (VstitchUserName),
    CONSTRAINT uq_vstitch_users_email UNIQUE (Email),
    CONSTRAINT uq_vstitch_users_phone UNIQUE (PhoneNumber),
    CONSTRAINT uq_vstitch_users_google_id UNIQUE (GoogleId)
);
