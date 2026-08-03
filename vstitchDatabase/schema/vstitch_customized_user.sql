-- VSTITCH_CUSTOMIZED_USER: one row per "Need a Custom Outfit?" lead
-- submitted through the VStitch AI widget (src/components/VstitchAiWidget.jsx)
-- - captured purely for admin follow-up / future leads-generation dashboard,
-- independent of the admin-notification email sent for the same submission
-- (the email can fail without losing the lead, and vice versa - see
-- CustomizationInterestService). No FK to VStitch_Users: this form is
-- reachable while logged out and isn't tied to an account.
-- Engine: PostgreSQL. Added by
-- migrations/0014_add_customized_user_leads.sql.

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
