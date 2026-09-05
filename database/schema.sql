-- ============================================================
-- BOI Banking Transaction Simulator - SQLite Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    account_id          TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    age                 INTEGER NOT NULL,
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,
    occupation          TEXT NOT NULL,
    customer_segment    TEXT NOT NULL,
    monthly_income      REAL NOT NULL,
    income_range        TEXT NOT NULL,
    account_open_date   TEXT NOT NULL,
    initial_balance     REAL NOT NULL,
    balance             REAL NOT NULL DEFAULT 0.0,
    risk_profile        TEXT NOT NULL,
    employer            TEXT,
    merchant_category   TEXT,
    cluster_id          TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'ACTIVE',
    activated_at        TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id  TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    sender_account  TEXT NOT NULL,
    receiver_account TEXT NOT NULL,
    amount          REAL NOT NULL,
    channel         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'COMPLETED',
    description     TEXT,
    relationship_type TEXT,
    simulated_day   INTEGER DEFAULT 0,
    risk_score      REAL DEFAULT 0.0,
    FOREIGN KEY (sender_account) REFERENCES accounts(account_id),
    FOREIGN KEY (receiver_account) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS account_profiles (
    account_id          TEXT PRIMARY KEY,
    avg_transaction_amt REAL DEFAULT 0.0,
    transaction_count   INTEGER DEFAULT 0,
    last_active         TEXT,
    risk_score          REAL DEFAULT 0.0,
    kyc_status          TEXT DEFAULT 'VERIFIED',
    occupation          TEXT,
    monthly_income      REAL DEFAULT 0.0,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS account_relationships (
    relationship_id     TEXT PRIMARY KEY,
    source_account      TEXT NOT NULL,
    target_account      TEXT NOT NULL,
    relationship_type   TEXT NOT NULL,
    strength            REAL NOT NULL,
    cluster_id          TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    last_seen_at        TEXT,
    FOREIGN KEY (source_account) REFERENCES accounts(account_id),
    FOREIGN KEY (target_account) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS mule_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    pattern_type    TEXT NOT NULL,
    chain_id        TEXT NOT NULL,
    layer           INTEGER DEFAULT 0,
    linked_account  TEXT,
    detected_at     TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS mule_networks (
    network_id      TEXT PRIMARY KEY,
    pattern_type    TEXT NOT NULL,
    source_account  TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    active          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fraud_events (
    event_id        TEXT PRIMARY KEY,
    transaction_id  TEXT,
    account_id      TEXT NOT NULL,
    fraud_type      TEXT NOT NULL,
    description     TEXT,
    severity        TEXT DEFAULT 'MEDIUM',
    detected_at     TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS graph_analytics (
    account_id              TEXT PRIMARY KEY,
    pagerank                REAL DEFAULT 0.0,
    degree_centrality       REAL DEFAULT 0.0,
    betweenness             REAL DEFAULT 0.0,
    community_id            TEXT,
    propagated_risk_score   REAL DEFAULT 0.0,
    updated_at              TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS system_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    log_level       TEXT NOT NULL,
    message         TEXT NOT NULL,
    component       TEXT DEFAULT 'COBOL_ENGINE',
    timestamp       TEXT NOT NULL
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_txn_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_txn_sender ON transactions(sender_account);
CREATE INDEX IF NOT EXISTS idx_txn_receiver ON transactions(receiver_account);
CREATE INDEX IF NOT EXISTS idx_mule_pattern ON mule_accounts(pattern_type);
CREATE INDEX IF NOT EXISTS idx_fraud_type ON fraud_events(fraud_type);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
CREATE INDEX IF NOT EXISTS idx_accounts_segment ON accounts(customer_segment);
CREATE INDEX IF NOT EXISTS idx_accounts_cluster ON accounts(cluster_id);
CREATE INDEX IF NOT EXISTS idx_relationship_source ON account_relationships(source_account);
CREATE INDEX IF NOT EXISTS idx_relationship_target ON account_relationships(target_account);
CREATE INDEX IF NOT EXISTS idx_relationship_type ON account_relationships(relationship_type);

-- Simulation control table
CREATE TABLE IF NOT EXISTS simulation_control (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TEXT
);
