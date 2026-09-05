/*
 * ============================================================
 * SQLite Bridge for GnuCOBOL Banking Engine
 * Provides C functions callable from COBOL for SQLite operations
 * ============================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sqlite3.h>

static sqlite3 *db = NULL;
/* Trim trailing spaces from COBOL strings */
static void trim_cobol_string(char *str, int len) {
    int i = len - 1;
    while (i >= 0 && (str[i] == ' ' || str[i] == '\0')) {
        str[i] = '\0';
        i--;
    }
}

/* Copy and trim a COBOL string */
static void copy_trim(char *dest, const char *src, int maxlen) {
    strncpy(dest, src, maxlen);
    dest[maxlen] = '\0';
    trim_cobol_string(dest, maxlen);
}

/* ============================================================
 * db_init - Open SQLite database
 * ============================================================ */
void db_init(char *path, int *path_len, int *result) {
    char clean_path[1024];
    copy_trim(clean_path, path, *path_len < 1023 ? *path_len : 1023);

    int rc = sqlite3_open(clean_path, &db);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "BRIDGE: Cannot open database: %s\n", sqlite3_errmsg(db));
        *result = -1;
        return;
    }

    /* Performance pragmas */
    sqlite3_exec(db, "PRAGMA journal_mode=WAL;", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA synchronous=NORMAL;", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA cache_size=10000;", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA temp_store=MEMORY;", NULL, NULL, NULL);

    fprintf(stdout, "BRIDGE: Database opened: %s\n", clean_path);
    fflush(stdout);
    *result = 0;
}

/* ============================================================
 * db_create_schema - Create all tables
 * ============================================================ */
void db_create_schema(int *result) {
    if (!db) { *result = -1; return; }
    char *err = NULL;

    const char *schema =
        "CREATE TABLE IF NOT EXISTS accounts ("
        "  account_id TEXT PRIMARY KEY,"
        "  account_name TEXT NOT NULL,"
        "  account_type TEXT NOT NULL DEFAULT 'SAVINGS',"
        "  status TEXT NOT NULL DEFAULT 'ACTIVE',"
        "  balance REAL NOT NULL DEFAULT 0.0,"
        "  phone TEXT,"
        "  created_at TEXT NOT NULL,"
        "  updated_at TEXT"
        ");"
        "CREATE TABLE IF NOT EXISTS transactions ("
        "  transaction_id TEXT PRIMARY KEY,"
        "  timestamp TEXT NOT NULL,"
        "  sender_account TEXT NOT NULL,"
        "  receiver_account TEXT NOT NULL,"
        "  amount REAL NOT NULL,"
        "  channel TEXT NOT NULL,"
        "  status TEXT NOT NULL DEFAULT 'COMPLETED',"
        "  fraud_flag INTEGER NOT NULL DEFAULT 0,"
        "  mule_flag INTEGER NOT NULL DEFAULT 0,"
        "  description TEXT"
        ");"
        "CREATE TABLE IF NOT EXISTS account_profiles ("
        "  account_id TEXT PRIMARY KEY,"
        "  avg_transaction_amt REAL DEFAULT 0.0,"
        "  transaction_count INTEGER DEFAULT 0,"
        "  last_active TEXT,"
        "  risk_score REAL DEFAULT 0.0,"
        "  kyc_status TEXT DEFAULT 'VERIFIED',"
        "  occupation TEXT,"
        "  monthly_income REAL DEFAULT 0.0"
        ");"
        "CREATE TABLE IF NOT EXISTS mule_accounts ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  account_id TEXT NOT NULL,"
        "  pattern_type TEXT NOT NULL,"
        "  chain_id TEXT NOT NULL,"
        "  layer INTEGER DEFAULT 0,"
        "  linked_account TEXT,"
        "  detected_at TEXT"
        ");"
        "CREATE TABLE IF NOT EXISTS fraud_events ("
        "  event_id TEXT PRIMARY KEY,"
        "  transaction_id TEXT,"
        "  account_id TEXT NOT NULL,"
        "  fraud_type TEXT NOT NULL,"
        "  description TEXT,"
        "  severity TEXT DEFAULT 'MEDIUM',"
        "  detected_at TEXT NOT NULL"
        ");"
        "CREATE TABLE IF NOT EXISTS system_logs ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  log_level TEXT NOT NULL,"
        "  message TEXT NOT NULL,"
        "  component TEXT DEFAULT 'COBOL_ENGINE',"
        "  timestamp TEXT NOT NULL"
        ");"
        "CREATE TABLE IF NOT EXISTS simulation_control ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT NOT NULL,"
        "  updated_at TEXT"
        ");"
        "CREATE INDEX IF NOT EXISTS idx_txn_timestamp ON transactions(timestamp);"
        "CREATE INDEX IF NOT EXISTS idx_txn_sender ON transactions(sender_account);"
        "CREATE INDEX IF NOT EXISTS idx_txn_receiver ON transactions(receiver_account);"
        "CREATE INDEX IF NOT EXISTS idx_txn_fraud ON transactions(fraud_flag);"
        "CREATE INDEX IF NOT EXISTS idx_txn_mule ON transactions(mule_flag);"
        "CREATE INDEX IF NOT EXISTS idx_mule_pattern ON mule_accounts(pattern_type);"
        "CREATE INDEX IF NOT EXISTS idx_fraud_type ON fraud_events(fraud_type);"
        "CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);";

    int rc = sqlite3_exec(db, schema, NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "BRIDGE: Schema error: %s\n", err);
        sqlite3_free(err);
        *result = -1;
        return;
    }

    fprintf(stdout, "BRIDGE: Schema created successfully\n");
    fflush(stdout);
    *result = 0;
}

/* ============================================================
 * db_begin_txn / db_commit_txn - Transaction batching
 * ============================================================ */
void db_begin_txn(int *result) {
    if (!db) { *result = -1; return; }
    char *err = NULL;
    int rc = sqlite3_exec(db, "BEGIN TRANSACTION;", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "BRIDGE: BEGIN error: %s\n", err);
        sqlite3_free(err);
        *result = -1;
        return;
    }
    *result = 0;
}

void db_commit_txn(int *result) {
    if (!db) { *result = -1; return; }
    char *err = NULL;
    int rc = sqlite3_exec(db, "COMMIT;", NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "BRIDGE: COMMIT error: %s\n", err);
        sqlite3_free(err);
        *result = -1;
        return;
    }
    *result = 0;
}

/* ============================================================
 * db_insert_account - Insert a single account
 * ============================================================ */
void db_insert_account(
    char *acct_id, int *id_len,
    char *acct_name, int *name_len,
    char *acct_type, int *type_len,
    char *status, int *status_len,
    double *balance,
    char *phone, int *phone_len,
    char *created_at, int *created_len,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_id[64], c_name[128], c_type[32], c_status[16], c_phone[32], c_created[32];
    copy_trim(c_id, acct_id, *id_len < 63 ? *id_len : 63);
    copy_trim(c_name, acct_name, *name_len < 127 ? *name_len : 127);
    copy_trim(c_type, acct_type, *type_len < 31 ? *type_len : 31);
    copy_trim(c_status, status, *status_len < 15 ? *status_len : 15);
    copy_trim(c_phone, phone, *phone_len < 31 ? *phone_len : 31);
    copy_trim(c_created, created_at, *created_len < 31 ? *created_len : 31);

    char sql[1024];
    snprintf(sql, sizeof(sql),
        "INSERT OR IGNORE INTO accounts (account_id, account_name, account_type, "
        "status, balance, phone, created_at) VALUES ('%s','%s','%s','%s',%.2f,'%s','%s');",
        c_id, c_name, c_type, c_status, *balance, c_phone, c_created);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "BRIDGE: Insert account error: %s\n", err);
        sqlite3_free(err);
        *result = -1;
        return;
    }
    *result = 0;
}

/* ============================================================
 * db_insert_profile - Insert account profile
 * ============================================================ */
void db_insert_profile(
    char *acct_id, int *id_len,
    double *avg_amt,
    double *monthly_income,
    char *occupation, int *occ_len,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_id[64], c_occ[64];
    copy_trim(c_id, acct_id, *id_len < 63 ? *id_len : 63);
    copy_trim(c_occ, occupation, *occ_len < 63 ? *occ_len : 63);

    char sql[512];
    snprintf(sql, sizeof(sql),
        "INSERT OR IGNORE INTO account_profiles (account_id, avg_transaction_amt, "
        "monthly_income, occupation) VALUES ('%s',%.2f,%.2f,'%s');",
        c_id, *avg_amt, *monthly_income, c_occ);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) { sqlite3_free(err); *result = -1; return; }
    *result = 0;
}

/* ============================================================
 * db_insert_transaction - Insert a single transaction
 * ============================================================ */
void db_insert_transaction(
    char *txn_id, int *txn_id_len,
    char *timestamp, int *ts_len,
    char *sender, int *sender_len,
    char *receiver, int *receiver_len,
    double *amount,
    char *channel, int *channel_len,
    char *status, int *status_len,
    int *fraud_flag,
    int *mule_flag,
    char *description, int *desc_len,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_txn[64], c_ts[32], c_sender[64], c_recv[64];
    char c_channel[32], c_status[32], c_desc[256];
    copy_trim(c_txn, txn_id, *txn_id_len < 63 ? *txn_id_len : 63);
    copy_trim(c_ts, timestamp, *ts_len < 31 ? *ts_len : 31);
    copy_trim(c_sender, sender, *sender_len < 63 ? *sender_len : 63);
    copy_trim(c_recv, receiver, *receiver_len < 63 ? *receiver_len : 63);
    copy_trim(c_channel, channel, *channel_len < 31 ? *channel_len : 31);
    copy_trim(c_status, status, *status_len < 31 ? *status_len : 31);
    copy_trim(c_desc, description, *desc_len < 255 ? *desc_len : 255);

    char sql[1024];
    snprintf(sql, sizeof(sql),
        "INSERT INTO transactions (transaction_id, timestamp, sender_account, "
        "receiver_account, amount, channel, status, fraud_flag, mule_flag, "
        "description) VALUES ('%s','%s','%s','%s',%.2f,'%s','%s',%d,%d,'%s');",
        c_txn, c_ts, c_sender, c_recv, *amount,
        c_channel, c_status, *fraud_flag, *mule_flag, c_desc);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "BRIDGE: Insert txn error: %s\n", err);
        sqlite3_free(err);
        *result = -1;
        return;
    }
    *result = 0;
}

/* ============================================================
 * db_insert_fraud_event - Insert fraud event
 * ============================================================ */
void db_insert_fraud_event(
    char *event_id, int *eid_len,
    char *txn_id, int *tid_len,
    char *acct_id, int *aid_len,
    char *fraud_type, int *ft_len,
    char *description, int *desc_len,
    char *severity, int *sev_len,
    char *detected_at, int *det_len,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_eid[64], c_tid[64], c_aid[64], c_ft[64], c_desc[256], c_sev[16], c_det[32];
    copy_trim(c_eid, event_id, *eid_len < 63 ? *eid_len : 63);
    copy_trim(c_tid, txn_id, *tid_len < 63 ? *tid_len : 63);
    copy_trim(c_aid, acct_id, *aid_len < 63 ? *aid_len : 63);
    copy_trim(c_ft, fraud_type, *ft_len < 63 ? *ft_len : 63);
    copy_trim(c_desc, description, *desc_len < 255 ? *desc_len : 255);
    copy_trim(c_sev, severity, *sev_len < 15 ? *sev_len : 15);
    copy_trim(c_det, detected_at, *det_len < 31 ? *det_len : 31);

    char sql[1024];
    snprintf(sql, sizeof(sql),
        "INSERT INTO fraud_events (event_id, transaction_id, account_id, "
        "fraud_type, description, severity, detected_at) "
        "VALUES ('%s','%s','%s','%s','%s','%s','%s');",
        c_eid, c_tid, c_aid, c_ft, c_desc, c_sev, c_det);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) { sqlite3_free(err); *result = -1; return; }
    *result = 0;
}

/* ============================================================
 * db_insert_mule - Insert mule account record
 * ============================================================ */
void db_insert_mule(
    char *acct_id, int *aid_len,
    char *pattern, int *pat_len,
    char *chain_id, int *chain_len,
    int *layer,
    char *linked, int *link_len,
    char *detected, int *det_len,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_aid[64], c_pat[32], c_chain[64], c_link[64], c_det[32];
    copy_trim(c_aid, acct_id, *aid_len < 63 ? *aid_len : 63);
    copy_trim(c_pat, pattern, *pat_len < 31 ? *pat_len : 31);
    copy_trim(c_chain, chain_id, *chain_len < 63 ? *chain_len : 63);
    copy_trim(c_link, linked, *link_len < 63 ? *link_len : 63);
    copy_trim(c_det, detected, *det_len < 31 ? *det_len : 31);

    char sql[512];
    snprintf(sql, sizeof(sql),
        "INSERT INTO mule_accounts (account_id, pattern_type, chain_id, "
        "layer, linked_account, detected_at) "
        "VALUES ('%s','%s','%s',%d,'%s','%s');",
        c_aid, c_pat, c_chain, *layer, c_link, c_det);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) { sqlite3_free(err); *result = -1; return; }
    *result = 0;
}

/* ============================================================
 * db_insert_log - Insert system log
 * ============================================================ */
void db_insert_log(
    char *level, int *level_len,
    char *message, int *msg_len,
    char *timestamp, int *ts_len,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_level[16], c_msg[512], c_ts[32];
    copy_trim(c_level, level, *level_len < 15 ? *level_len : 15);
    copy_trim(c_msg, message, *msg_len < 511 ? *msg_len : 511);
    copy_trim(c_ts, timestamp, *ts_len < 31 ? *ts_len : 31);

    char sql[1024];
    snprintf(sql, sizeof(sql),
        "INSERT INTO system_logs (log_level, message, timestamp) "
        "VALUES ('%s','%s','%s');",
        c_level, c_msg, c_ts);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) { sqlite3_free(err); *result = -1; return; }
    *result = 0;
}

/* ============================================================
 * db_update_balance - Update account balance
 * ============================================================ */
void db_update_balance(
    char *acct_id, int *id_len,
    double *new_balance,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_id[64];
    copy_trim(c_id, acct_id, *id_len < 63 ? *id_len : 63);

    char sql[256];
    snprintf(sql, sizeof(sql),
        "UPDATE accounts SET balance=%.2f, updated_at=datetime('now') "
        "WHERE account_id='%s';", *new_balance, c_id);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) { sqlite3_free(err); *result = -1; return; }
    *result = 0;
}

/* ============================================================
 * db_update_sim_control - Update simulation control value
 * ============================================================ */
void db_update_sim_control(
    char *key, int *key_len,
    char *value, int *val_len,
    int *result
) {
    if (!db) { *result = -1; return; }

    char c_key[64], c_val[256];
    copy_trim(c_key, key, *key_len < 63 ? *key_len : 63);
    copy_trim(c_val, value, *val_len < 255 ? *val_len : 255);

    char sql[512];
    snprintf(sql, sizeof(sql),
        "INSERT OR REPLACE INTO simulation_control (key, value, updated_at) "
        "VALUES ('%s','%s',datetime('now'));", c_key, c_val);

    char *err = NULL;
    int rc = sqlite3_exec(db, sql, NULL, NULL, &err);
    if (rc != SQLITE_OK) { sqlite3_free(err); *result = -1; return; }
    *result = 0;
}

/* ============================================================
 * db_check_stop - Check if stop signal file exists
 * ============================================================ */
void db_check_stop(char *path, int *path_len, int *result) {
    char clean_path[1024];
    copy_trim(clean_path, path, *path_len < 1023 ? *path_len : 1023);

    FILE *f = fopen(clean_path, "r");
    if (f) {
        fclose(f);
        *result = 1;  /* Stop signal found */
    } else {
        *result = 0;  /* No stop signal */
    }
}

/* ============================================================
 * db_close_db - Close SQLite database
 * ============================================================ */
void db_close_db(int *result) {
    if (db) {
        sqlite3_close(db);
        db = NULL;
        fprintf(stdout, "BRIDGE: Database closed\n");
        fflush(stdout);
    }
    *result = 0;
}
