-- Migration: adds VSTITCH_PASSWORD_RESET_OTPS for the "Forgot password?"
-- email-OTP flow - see vstitchDatabase/schema/vstitch_password_reset_otps.sql
-- for the full rationale.
--
-- Run once, directly against Supabase (matches how 0004/0006-0015 were
-- applied - see README "Database schema").

CREATE TABLE IF NOT EXISTS VSTITCH_PASSWORD_RESET_OTPS (
    VstitchPasswordResetOtpId BIGSERIAL     PRIMARY KEY,
    VstitchUserId             BIGINT        NOT NULL UNIQUE REFERENCES VStitch_Users (VstitchUserId) ON DELETE CASCADE,
    OtpHash                   VARCHAR(250)  NOT NULL,
    ExpiresAt                 TIMESTAMP     NOT NULL,
    ConsumedAt                TIMESTAMP,
    AttemptCount              INT           NOT NULL DEFAULT 0,
    created_by                VARCHAR(250)  NOT NULL,
    created_date               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by                VARCHAR(250)  NOT NULL,
    updated_date               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_reset_otps_expires_at ON VSTITCH_PASSWORD_RESET_OTPS (ExpiresAt);
