-- VStitch_Addresses: reusable shipping/billing addresses per user. Depends on VStitch_Users.
-- Engine: PostgreSQL.

CREATE TABLE IF NOT EXISTS VStitch_Addresses (
    VstitchAddressId  BIGSERIAL     PRIMARY KEY,
    VstitchUserId     BIGINT        NOT NULL REFERENCES VStitch_Users(VstitchUserId) ON DELETE CASCADE,
    AddressType       VARCHAR(20)   NOT NULL DEFAULT 'shipping' CHECK (AddressType IN ('shipping', 'billing')),
    RecipientName     VARCHAR(250)  NOT NULL,
    AddressLine1      VARCHAR(250)  NOT NULL,
    AddressLine2      VARCHAR(250),
    City              VARCHAR(250)  NOT NULL,
    State             VARCHAR(250)  NOT NULL,
    PostalCode        VARCHAR(20)   NOT NULL,
    Country           VARCHAR(250)  NOT NULL,
    PhoneNumber       VARCHAR(250)  NOT NULL,
    IsDefault         BOOLEAN       NOT NULL DEFAULT FALSE,
    created_by        VARCHAR(250)  NOT NULL,
    created_date      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by        VARCHAR(250),
    updated_date      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_addresses_user_id ON VStitch_Addresses (VstitchUserId);
