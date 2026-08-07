-- Migration: adds VSTITCH_SUBSCRIBERS for the newsletter "Subscribe" form -
-- see vstitchDatabase/schema/vstitch_subscribers.sql for the full rationale.
--
-- Run once, directly against Supabase (matches how 0004/0006-0014 were
-- applied - see README "Database schema").

CREATE TABLE IF NOT EXISTS VSTITCH_SUBSCRIBERS (
    VstitchSubscriberId BIGSERIAL     PRIMARY KEY,
    Email                VARCHAR(250)  NOT NULL UNIQUE,
    created_by           VARCHAR(250)  NOT NULL,
    created_date         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by           VARCHAR(250)  NOT NULL,
    updated_date         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscribers_created_date ON VSTITCH_SUBSCRIBERS (created_date);
