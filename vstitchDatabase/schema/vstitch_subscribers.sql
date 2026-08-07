-- VSTITCH_SUBSCRIBERS: one row per email address that has hit the
-- newsletter "Subscribe" button - captured purely for the studio's mailing
-- list, independent of any customer account. No FK to VStitch_Users: this
-- form is reachable while logged out and isn't tied to an account, same as
-- VSTITCH_CUSTOMIZED_USER. Email is UNIQUE: re-subscribing with an email
-- already on file is idempotent (bumps updated_by/updated_date instead of
-- erroring or creating a duplicate row) - see subscriber_queries.yaml's
-- insert_subscriber ON CONFLICT clause.
-- Engine: PostgreSQL. Added by migrations/0015_add_subscribers.sql.

CREATE TABLE IF NOT EXISTS VSTITCH_SUBSCRIBERS (
    VstitchSubscriberId BIGSERIAL     PRIMARY KEY,
    Email                VARCHAR(250)  NOT NULL UNIQUE,
    created_by           VARCHAR(250)  NOT NULL,
    created_date         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by           VARCHAR(250)  NOT NULL,
    updated_date         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscribers_created_date ON VSTITCH_SUBSCRIBERS (created_date);
