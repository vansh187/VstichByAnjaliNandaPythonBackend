-- VStitch_Users: signup/authentication table for the VStitch ecommerce backend.
-- Engine: PostgreSQL (psycopg2 / SQLAlchemy per requirements.txt).
-- VstitchPassword stores a bcrypt hash (via passlib); JWTs are issued separately
-- using JWT_SECRET / JWT_ALGORITHM (HS256) from .env after successful login.
--
-- Also backs Google OAuth login (see migrations/0007_add_google_oauth_login.sql):
-- GoogleId is Google's stable `sub` claim, AuthProvider is 'local' or 'google'.
-- VstitchPassword/PhoneNumber are nullable because a Google-only account never
-- collects either.
--
-- LocationPermissionGranted/GoogleMapsLink capture the browser geolocation
-- prompt's result - set at signup if granted, refreshed on every later
-- login via POST /users/location. Both nullable: denied/dismissed/
-- unsupported-browser, or an account predating this feature, all mean "no
-- value", not an error. GoogleMapsLink stores a ready-to-open Maps URL
-- built client-side (https://www.google.com/maps?q=<lat>,<lng>), not raw
-- coordinates - see migrations/0018_replace_user_location_with_maps_link.sql
-- (superseding migrations/0017_add_user_location.sql's original
-- Latitude/Longitude columns, dropped in 0018).

CREATE TABLE IF NOT EXISTS VStitch_Users (
    VstitchUserId              BIGSERIAL         PRIMARY KEY,
    VstitchUserName            VARCHAR(250)      NOT NULL,
    VstitchPassword            VARCHAR(250),
    FirstName                  VARCHAR(250)      NOT NULL,
    LastName                   VARCHAR(250)      NOT NULL,
    Email                      VARCHAR(250)      NOT NULL,
    PhoneNumber                VARCHAR(250),
    GoogleId                   VARCHAR(250),
    AuthProvider               VARCHAR(20)       NOT NULL DEFAULT 'local',
    LocationPermissionGranted  BOOLEAN,
    GoogleMapsLink              TEXT,
    created_by                 VARCHAR(250)      NOT NULL,
    created_date               TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by                 VARCHAR(250),
    updated_date               TIMESTAMP,

    CONSTRAINT uq_vstitch_users_username UNIQUE (VstitchUserName),
    CONSTRAINT uq_vstitch_users_email UNIQUE (Email),
    CONSTRAINT uq_vstitch_users_phone UNIQUE (PhoneNumber),
    CONSTRAINT uq_vstitch_users_google_id UNIQUE (GoogleId)
);
