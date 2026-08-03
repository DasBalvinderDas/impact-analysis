CREATE TABLE invoices (
    invoice_id VARCHAR(64) PRIMARY KEY,
    legacy_customer_id VARCHAR(64) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoices_legacy_customer_id
    ON invoices (legacy_customer_id);

CREATE TABLE user_preferences (
    customer_id VARCHAR(64) PRIMARY KEY,
    invoice_email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
