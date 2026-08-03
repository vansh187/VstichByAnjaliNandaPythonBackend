-- Migration: adds VSTITCH_CUSTOMIZED_USER for the VStitch AI widget's
-- "Need a Custom Outfit?" lead-capture form - see vstitchDatabase/schema/
-- vstitch_customized_user.sql for the full rationale.
--
-- Run once, directly against Supabase (matches how 0004/0006-0013 were
-- applied - see README "Database schema").

CREATE TABLE IF NOT EXISTS VSTITCH_CUSTOMIZED_USER (
    VstitchCustomizedUserId BIGSERIAL     PRIMARY KEY,
    CustomerName            VARCHAR(250)  NOT NULL,
    CustomerPhone           VARCHAR(50)   NOT NULL,
    CustomerEmail           VARCHAR(250)  NOT NULL,
    created_by              VARCHAR(250)  NOT NULL,
    created_date            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customized_user_email ON VSTITCH_CUSTOMIZED_USER (CustomerEmail);
CREATE INDEX IF NOT EXISTS idx_customized_user_created_date ON VSTITCH_CUSTOMIZED_USER (created_date);
