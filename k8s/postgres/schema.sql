CREATE TABLE IF NOT EXISTS fraud_decisions (
    id                  SERIAL PRIMARY KEY,
    transaction_id      UUID NOT NULL UNIQUE,
    user_id             VARCHAR(64) NOT NULL,
    amount              DECIMAL(15,2) NOT NULL,
    currency            VARCHAR(3) DEFAULT 'USD',
    merchant_name       VARCHAR(255),
    merchant_category   VARCHAR(64),
    merchant_country    VARCHAR(2),
    user_country        VARCHAR(2),
    payment_method      VARCHAR(32),
    channel             VARCHAR(16),
    ml_score            DECIMAL(8,6) NOT NULL,
    rules_score         DECIMAL(8,6) NOT NULL,
    final_score         DECIMAL(8,6) NOT NULL,
    decision            VARCHAR(16) NOT NULL,   -- APPROVE / REVIEW / BLOCK
    triggered_rules     JSONB DEFAULT '[]',
    is_fraud            BOOLEAN DEFAULT FALSE,
    fraud_pattern       VARCHAR(64),
    raw_transaction     JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_reviews (
    id                  SERIAL PRIMARY KEY,
    transaction_id      UUID NOT NULL REFERENCES fraud_decisions(transaction_id),
    analyst_id          VARCHAR(64) NOT NULL,
    analyst_decision    VARCHAR(16) NOT NULL,   -- CONFIRMED_FRAUD / FALSE_POSITIVE / NEEDS_INFO
    notes               TEXT,
    reviewed_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_log (
    id                  SERIAL PRIMARY KEY,
    transaction_id      UUID NOT NULL,
    alert_type          VARCHAR(32) NOT NULL,   -- EMAIL / WEBHOOK
    recipient           VARCHAR(255),
    status              VARCHAR(16) NOT NULL,   -- SENT / FAILED
    payload             JSONB,
    sent_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_user_id    ON fraud_decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_decision   ON fraud_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON fraud_decisions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_is_fraud   ON fraud_decisions(is_fraud);