-- Migration: adds geolocation columns to VStitch_Users for the
-- "save customer location" feature - captured once at signup (if the
-- browser's geolocation prompt was granted) and refreshed on every
-- subsequent login via POST /users/location.
--
-- All three columns are nullable: NULL covers every account that predates
-- this feature, plus every current signup/login where the shopper denied
-- or dismissed the prompt, or the browser doesn't support geolocation at
-- all - none of those are validation errors, just "no value to store".
-- Latitude/Longitude are DOUBLE PRECISION, not VARCHAR - a numeric type
-- has no string-length truncation to worry about and no parsing needed on
-- read, unlike the VARCHAR(n) columns used for text fields elsewhere in
-- this table.
--
-- Run once, directly against Supabase (matches how 0004/0006-0016 were
-- applied - see README "Database schema"). Also mirrored into
-- SchemaPersistence.create_users_table_if_not_exists() via
-- user_queries.yaml's create_table, since VStitch_Users is foundational
-- infra applied at app boot (see 0007's matching comment).

ALTER TABLE VStitch_Users
    ADD COLUMN IF NOT EXISTS LocationPermissionGranted BOOLEAN,
    ADD COLUMN IF NOT EXISTS Latitude                  DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS Longitude                 DOUBLE PRECISION;
