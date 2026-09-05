-- ============================================================
-- BOI Banking Transaction Simulator - Schema V2
-- Real Bank Dataset (Regulatory Feed) Support
-- ============================================================
-- SAFE: All statements use IF NOT EXISTS / INSERT OR IGNORE.
-- Existing v1 tables are NOT modified in any way.
-- ============================================================

-- -----------------------------------------------------------------
-- 1. data_source_registry
--    Tracks which data source is currently active so the frontend
--    and API can determine whether to serve COBOL or real bank data.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_source_registry (
    source_id       TEXT PRIMARY KEY,
    source_name     TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK (source_type IN ('COBOL_SYNTHETIC', 'REGULATORY_FEED')),
    file_path       TEXT,
    row_count       INTEGER DEFAULT 0,
    mule_count      INTEGER DEFAULT 0,
    ingested_at     TEXT,
    is_active       INTEGER DEFAULT 0
);

-- -----------------------------------------------------------------
-- 2. dataset_accounts
--    Demographic/profile portion of DataSet.csv rows, mapped to be
--    compatible with the existing accounts table structure.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dataset_accounts (
    account_id          TEXT PRIMARY KEY,
    source_row_index    INTEGER NOT NULL,
    account_type        TEXT,          -- F3886: Savings / Current
    registration_date   TEXT,          -- F3888 parsed to ISO YYYY-MM-DD
    scheme_code         TEXT,          -- F3889
    region_code         TEXT,          -- F3890
    occupation          TEXT,          -- F3891 normalised UPPERCASE
    gender              TEXT,          -- F3892
    segment             TEXT,          -- F3893: RETAIL / CORPORATE
    f3887_value         INTEGER,       -- F3887 unnamed numeric
    f3894               INTEGER,
    f3895               INTEGER,
    f3896               INTEGER,
    f3897               INTEGER,
    f3898               INTEGER,
    f3899               INTEGER,
    f3900               INTEGER,
    f3901               INTEGER,
    f3902               INTEGER,
    f3903               INTEGER,
    f3904               INTEGER,
    f3905               INTEGER,
    f3906               INTEGER,
    f3907               INTEGER,
    f3908               INTEGER,
    f3909               INTEGER,
    f3910               INTEGER,
    f3911               INTEGER,
    f3912               INTEGER,
    f3913               INTEGER,
    f3914               INTEGER,
    f3915               INTEGER,
    f3916               INTEGER,
    f3917               INTEGER,
    f3918               INTEGER,
    f3919               INTEGER,
    f3920               INTEGER,
    f3921               INTEGER,
    f3922               INTEGER,
    f3923               INTEGER,
    is_mule             INTEGER DEFAULT 0,   -- F3924
    risk_profile        TEXT DEFAULT 'UNKNOWN',
    status              TEXT DEFAULT 'ACTIVE',
    data_source         TEXT DEFAULT 'REGULATORY_FEED',
    ingested_at         TEXT DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------
-- 3. dataset_features
--    Sparse key-value store for F1–F3885 numeric features.
--    Only non-null values from dense features are persisted.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dataset_features (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    feature_name    TEXT NOT NULL,
    feature_value   REAL NOT NULL,
    FOREIGN KEY (account_id) REFERENCES dataset_accounts(account_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ds_features_account_name
    ON dataset_features(account_id, feature_name);

-- -----------------------------------------------------------------
-- 4. dataset_transactions_synthetic
--    Synthetically reconstructed transactions from behavioral
--    aggregate columns F3894–F3923, for dashboard rendering when
--    DataSet.csv is the active source.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dataset_transactions_synthetic (
    transaction_id      TEXT PRIMARY KEY,
    timestamp           TEXT NOT NULL,
    sender_account      TEXT NOT NULL,
    receiver_account    TEXT NOT NULL,
    amount              REAL NOT NULL,
    channel             TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'COMPLETED',
    description         TEXT,
    relationship_type   TEXT,
    simulated_day       INTEGER DEFAULT 0,
    risk_score          REAL DEFAULT 0.0,
    data_source         TEXT DEFAULT 'REGULATORY_FEED',
    FOREIGN KEY (sender_account) REFERENCES dataset_accounts(account_id),
    FOREIGN KEY (receiver_account) REFERENCES dataset_accounts(account_id)
);

-- -----------------------------------------------------------------
-- 5. schema_version
--    Tracks which schema versions have been applied.
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version         INTEGER PRIMARY KEY,
    applied_at      TEXT NOT NULL,
    description     TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at, description)
    VALUES (1, datetime('now'), 'Initial COBOL schema');
INSERT OR IGNORE INTO schema_version (version, applied_at, description)
    VALUES (2, datetime('now'), 'Real bank dataset regulatory feed support');

-- -----------------------------------------------------------------
-- Indexes for dataset tables
-- -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ds_accounts_mule       ON dataset_accounts(is_mule);
CREATE INDEX IF NOT EXISTS idx_ds_accounts_segment    ON dataset_accounts(segment);
CREATE INDEX IF NOT EXISTS idx_ds_accounts_occupation ON dataset_accounts(occupation);
CREATE INDEX IF NOT EXISTS idx_ds_accounts_type       ON dataset_accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_ds_features_account    ON dataset_features(account_id);
CREATE INDEX IF NOT EXISTS idx_ds_features_name       ON dataset_features(feature_name);
CREATE INDEX IF NOT EXISTS idx_ds_txn_sender          ON dataset_transactions_synthetic(sender_account);
CREATE INDEX IF NOT EXISTS idx_ds_txn_receiver        ON dataset_transactions_synthetic(receiver_account);
CREATE INDEX IF NOT EXISTS idx_ds_source              ON dataset_accounts(data_source);
