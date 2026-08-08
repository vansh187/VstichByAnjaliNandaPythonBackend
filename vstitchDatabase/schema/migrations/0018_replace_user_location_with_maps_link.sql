-- Migration: replaces VStitch_Users.Latitude/Longitude (added by
-- migrations/0017_add_user_location.sql) with a single GoogleMapsLink
-- column - a revised spec: the frontend now builds and sends a
-- ready-to-open Google Maps URL (https://www.google.com/maps?q=<lat>,<lng>)
-- client-side, rather than raw coordinates, so a human (e.g. support staff
-- looking at an order) can click straight into a map instead of pasting
-- two floats into a maps tool themselves.
--
-- Nullable, no default, TEXT (not VARCHAR(n)) - same rationale as 0017:
-- denied/dismissed/unsupported-browser/pre-feature accounts all mean "no
-- value", and a URL has no natural fixed length to cap without risking
-- truncating a legitimate one.
--
-- Run once, directly against Supabase (matches how 0004/0006-0017 were
-- applied - see README "Database schema"). Also mirrored into
-- SchemaPersistence.create_users_table_if_not_exists() via
-- user_queries.yaml's create_table, since VStitch_Users is foundational
-- infra applied at app boot (see 0007's matching comment).

ALTER TABLE VStitch_Users
    ADD COLUMN IF NOT EXISTS GoogleMapsLink TEXT;

ALTER TABLE VStitch_Users
    DROP COLUMN IF EXISTS Latitude,
    DROP COLUMN IF EXISTS Longitude;
