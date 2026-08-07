-- VSTITCH_PASSWORD_RESET_OTPS: at most one row per user - the "Forgot
-- password?" flow's active OTP. VstitchUserId is UNIQUE (not just indexed):
-- requesting a new code upserts this row (see password_reset_queries.yaml's
-- upsert_otp ON CONFLICT clause), which is what makes "generating a new
-- code invalidates the previous one" true by construction rather than
-- needing a separate cleanup step. OtpHash stores a bcrypt hash of the
-- 6-digit code (via PasswordHashService, the same hasher used for account
-- passwords), never the raw code. ConsumedAt is set once the code is used
-- successfully, so it can't be replayed even before ExpiresAt. AttemptCount
-- tracks failed /confirm attempts for this code, capped in
-- PasswordResetService (MAX_OTP_ATTEMPTS) so a 6-digit code can't be
-- brute-forced within its 10-minute window.
-- Engine: PostgreSQL. Added by
-- migrations/0016_add_password_reset_otps.sql.

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
