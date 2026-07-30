-- Migration: adds Google OAuth login to VStitch_Users, alongside the
-- existing username/password login (this table now serves both).
--
-- GoogleId stores the token's stable `sub` claim (Google's own user id -
-- never reused, unlike email). AuthProvider records how the account was
-- created/last authenticated ('local' or 'google') for a quick per-row
-- check without inferring it from which columns are NULL.
--
-- VstitchPassword and PhoneNumber drop to nullable: a Google sign-in never
-- collects a password, and Google's ID token doesn't carry a phone number,
-- so neither can be required at insert time for a Google-only account.
-- Existing local accounts are unaffected (both columns stay populated).
--
-- Run once, directly against Supabase (matches how 0004/0006 were applied -
-- see README "Database schema"). Also mirrored into
-- SchemaPersistence.create_users_table_if_not_exists() via user_queries.yaml's
-- create_table, since VStitch_Users is foundational infra applied at app
-- boot the same way VStitch_AdminUsers is (see 0006's comment).

ALTER TABLE VStitch_Users
    ADD COLUMN IF NOT EXISTS GoogleId     VARCHAR(250),
    ADD COLUMN IF NOT EXISTS AuthProvider VARCHAR(20) NOT NULL DEFAULT 'local';

ALTER TABLE VStitch_Users
    ALTER COLUMN VstitchPassword DROP NOT NULL,
    ALTER COLUMN PhoneNumber DROP NOT NULL;

ALTER TABLE VStitch_Users
    DROP CONSTRAINT IF EXISTS uq_vstitch_users_google_id;
ALTER TABLE VStitch_Users
    ADD CONSTRAINT uq_vstitch_users_google_id UNIQUE (GoogleId);
