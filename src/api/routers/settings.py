"""Settings page backend — generator control, DB reset, user profile.

Endpoints
---------
POST   /settings/generator/run     — launch guard.sh with SSE streaming
GET    /settings/generator/status   — is a generator process running?
DELETE /settings/database           — wipe + reinitialise schema
GET    /settings/profile            — read user profile
PATCH  /settings/profile            — update user profile
"""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.deps import get_db
from src.config import SQLITE_DB_PATH

router = APIRouter(tags=["Settings"])

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]  # …/BOI
SCHEMA_V1 = ROOT / "database" / "schema.sql"
SCHEMA_V2 = ROOT / "database" / "schema_v2.sql"
GUARD_SH = ROOT / "guard.sh"
DELETION_LOG = ROOT / "database" / "deletion_log.txt"

# ---------------------------------------------------------------------------
# Module-level singleton tracking the active generator process
# ---------------------------------------------------------------------------
_active_process: subprocess.Popen | None = None


# ===================================================================
# 1. POST /settings/generator/run  — SSE streaming
# ===================================================================

VALID_SPEEDS = {"1x", "2x", "5x", "10x", "20x", "100x", "1000x"}

class GeneratorRunRequest(BaseModel):
    accounts: int = Field(ge=1000, le=500000)
    transactions: int = Field(ge=1000, le=500000)
    speed: str


@router.post("/generator/run")
async def generator_run(body: GeneratorRunRequest):
    global _active_process

    # Validate speed
    if body.speed not in VALID_SPEEDS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid speed '{body.speed}'. Must be one of {sorted(VALID_SPEEDS)}",
        )

    # Prevent double-launch
    if _active_process is not None and _active_process.poll() is None:
        raise HTTPException(status_code=409, detail="Generator already running")

    env = {
        **os.environ,
        "BOI_ACCOUNTS": str(body.accounts),
        "BOI_TRANSACTIONS": str(body.transactions),
        "BOI_SPEED": body.speed,
    }

    proc = subprocess.Popen(
        ["bash", str(GUARD_SH)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=env,
        text=True,
        bufsize=1,  # line-buffered
    )
    _active_process = proc

    def _stream():
        global _active_process
        try:
            for line in iter(proc.stdout.readline, ""):
                payload = json.dumps({"line": line.rstrip("\n")})
                yield f"data: {payload}\n\n"
            proc.stdout.close()
            proc.wait()
            yield f"data: {json.dumps({'exit_code': proc.returncode})}\n\n"
        finally:
            _active_process = None

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ===================================================================
# 2. GET /settings/generator/status
# ===================================================================

@router.get("/generator/status")
def generator_status():
    if _active_process is not None and _active_process.poll() is None:
        return {"running": True, "pid": _active_process.pid}
    return {"running": False, "pid": None}


# ===================================================================
# 3. DELETE /settings/database  — full wipe + schema re-init
# ===================================================================

class DatabaseDeleteRequest(BaseModel):
    confirmation: str


@router.delete("/database")
def delete_database(
    request: Request,
    body: Optional[DatabaseDeleteRequest] = None
):
    token = request.headers.get("X-Confirm-Token")
    
    confirmed = False
    if token and token.strip():
        confirmed = True
    elif body and body.confirmation == "DELETE":
        confirmed = True
        
    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail="Requires X-Confirm-Token header OR confirmation='DELETE' in request body."
        )

    # Determine unique DB paths to clear (both banking.db and ecosystem.db/active config)
    db_paths = {str(ROOT / "database" / "banking.db")}
    active_path = Path(SQLITE_DB_PATH)
    if not active_path.is_absolute():
        active_path = ROOT / active_path
    db_paths.add(str(active_path.resolve()))

    schema_version = 1
    tables_dropped_all = {}

    for path_str in db_paths:
        path = Path(path_str)
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Check if schema_v2 tables existed before dropping
        has_v2 = False
        try:
            conn.execute("SELECT 1 FROM schema_version LIMIT 1")
            has_v2 = True
        except sqlite3.OperationalError:
            pass

        # Get all user tables and drop them
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for table in tables:
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.commit()

        # Re-apply base schema
        conn.executescript(SCHEMA_V1.read_text(encoding="utf-8"))

        # Re-apply v2 if it was present or if v2 file exists
        if has_v2 or SCHEMA_V2.exists():
            conn.executescript(SCHEMA_V2.read_text(encoding="utf-8"))
            schema_version = 2

        # Add settings_profile table (may be needed fresh)
        conn.executescript(_SETTINGS_PROFILE_DDL)
        conn.commit()
        conn.close()
        
        tables_dropped_all[path.name] = tables

    # Audit log
    DELETION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(DELETION_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] Database wiped. "
                f"Paths processed: {list(db_paths)}. Tables dropped: {tables_dropped_all}. "
                f"Schema re-applied: v{schema_version}\n")

    return {"success": True, "schema_version": schema_version}


@router.delete("/database/transactions")
def clear_transactions(
    request: Request,
    body: Optional[DatabaseDeleteRequest] = None
):
    token = request.headers.get("X-Confirm-Token")
    confirmed = False
    if token and token.strip():
        confirmed = True
    elif body and body.confirmation == "DELETE":
        confirmed = True
        
    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail="Requires X-Confirm-Token header OR confirmation='DELETE' in request body."
        )

    db_paths = {str(ROOT / "database" / "banking.db")}
    active_path = Path(SQLITE_DB_PATH)
    if not active_path.is_absolute():
        active_path = ROOT / active_path
    db_paths.add(str(active_path.resolve()))

    for path_str in db_paths:
        path = Path(path_str)
        if path.exists():
            conn = sqlite3.connect(str(path), check_same_thread=False)
            try:
                conn.execute("PRAGMA foreign_keys = OFF")
                tables = ["transactions", "fraud_events", "dataset_features", "risk_metrics", "alert_resolutions", "alert_feedback"]
                for t in tables:
                    try:
                        conn.execute(f"DELETE FROM {t}")
                    except sqlite3.OperationalError:
                        pass
                conn.commit()
            finally:
                conn.close()
                
    return {"success": True}


@router.post("/database/rebuild")
def rebuild_database(
    request: Request,
    body: Optional[DatabaseDeleteRequest] = None
):
    return delete_database(request=request, body=body)


# ===================================================================
# 4. GET / PATCH  /settings/profile
# ===================================================================

_SETTINGS_PROFILE_DDL = """
CREATE TABLE IF NOT EXISTS settings_profile (
    user_id     TEXT PRIMARY KEY DEFAULT 'default',
    name        TEXT NOT NULL DEFAULT 'Admin',
    email       TEXT NOT NULL DEFAULT 'admin@boi.com',
    avatar_url  TEXT DEFAULT NULL,
    updated_at  TEXT
);
INSERT OR IGNORE INTO settings_profile (user_id, name, email, updated_at)
    VALUES ('default', 'Admin', 'admin@boi.com', datetime('now'));
"""


def _ensure_profile_table(db: sqlite3.Connection):
    """Idempotently create the settings_profile table + default row."""
    db.executescript(_SETTINGS_PROFILE_DDL)


class ProfilePatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


@router.get("/settings/profile")
def get_profile(db: sqlite3.Connection = Depends(get_db)):
    _ensure_profile_table(db)
    row = db.execute(
        "SELECT user_id, name, email, avatar_url, updated_at FROM settings_profile WHERE user_id = 'default'"
    ).fetchone()
    return dict(row) if row else {"user_id": "default", "name": "Admin", "email": "admin@boi.com", "avatar_url": None}


@router.patch("/settings/profile")
def patch_profile(body: ProfilePatch, db: sqlite3.Connection = Depends(get_db)):
    _ensure_profile_table(db)
    updates = []
    params = []
    if body.name is not None:
        updates.append("name = ?")
        params.append(body.name)
    if body.email is not None:
        updates.append("email = ?")
        params.append(body.email)
    if body.avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(body.avatar_url)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat(timespec="seconds"))
    params.append("default")

    db.execute(
        f"UPDATE settings_profile SET {', '.join(updates)} WHERE user_id = ?",
        params,
    )
    db.commit()

    row = db.execute(
        "SELECT user_id, name, email, avatar_url, updated_at FROM settings_profile WHERE user_id = 'default'"
    ).fetchone()
    return dict(row)


# ===================================================================
# 5. COBOL Simulator Engine Controls
# ===================================================================

@router.get("/cobol/status")
def get_cobol_status(db: sqlite3.Connection = Depends(get_db)):
    is_running = _active_process is not None and _active_process.poll() is None
    pid = _active_process.pid if is_running else None
    
    account_count = 0
    transaction_count = 0
    fraud_events_count = 0
    try:
        account_count = db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        transaction_count = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        fraud_events_count = db.execute("SELECT COUNT(*) FROM fraud_events").fetchone()[0]
    except Exception:
        pass
        
    return {
        "status": "Running" if is_running else "Stopped",
        "running": is_running,
        "pid": pid,
        "accounts_count": account_count,
        "transactions_count": transaction_count,
        "fraud_events_count": fraud_events_count,
    }


@router.post("/cobol/start")
def start_cobol():
    global _active_process
    if _active_process is not None and _active_process.poll() is None:
        raise HTTPException(status_code=409, detail="COBOL engine is already running")
        
    stop_file = ROOT / "runtime" / "guard.stop"
    if stop_file.exists():
        try:
            stop_file.unlink()
        except Exception:
            pass
            
    env = {
        **os.environ,
        "BOI_ACCOUNTS": "10000",
        "BOI_TRANSACTIONS": "50000",
        "BOI_SPEED": "100x",
    }
    
    proc = subprocess.Popen(
        ["bash", str(GUARD_SH)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=env,
        text=True,
        bufsize=1,
    )
    _active_process = proc
    return {"status": "success", "pid": proc.pid}


@router.post("/cobol/stop")
def stop_cobol():
    stop_file = ROOT / "runtime" / "guard.stop"
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    stop_file.write_text("STOP", encoding="utf-8")
    
    global _active_process
    if _active_process is not None and _active_process.poll() is None:
        time.sleep(0.5)
        if _active_process.poll() is None:
            try:
                _active_process.terminate()
            except Exception:
                pass
                
    return {"status": "success", "message": "COBOL engine termination requested."}


@router.post("/cobol/generate/{item_type}")
def cobol_generate(item_type: str):
    global _active_process
    if _active_process is not None and _active_process.poll() is None:
        raise HTTPException(status_code=409, detail="Engine is busy. Stop current simulation first.")

    accounts = "1000"
    txns = "5000"
    if item_type == "accounts":
        accounts = "10000"
        txns = "1"
    elif item_type == "transactions":
        accounts = "0"
        txns = "20000"
    elif item_type == "scenario":
        accounts = "2000"
        txns = "8000"

    env = {
        **os.environ,
        "BOI_ACCOUNTS": accounts,
        "BOI_TRANSACTIONS": txns,
        "BOI_SPEED": "1000x",
    }

    stop_file = ROOT / "runtime" / "guard.stop"
    if stop_file.exists():
        try:
            stop_file.unlink()
        except Exception:
            pass

    proc = subprocess.Popen(
        ["bash", str(GUARD_SH)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=env,
        text=True,
        bufsize=1,
    )
    _active_process = proc
    return {"status": "success", "pid": proc.pid, "item_type": item_type}


# ===================================================================
# 6. File browser & Ingestion Pipeline
# ===================================================================

@router.get("/settings/files")
def list_csv_files():
    import glob
    search_path = str(ROOT)
    csv_paths = glob.glob(os.path.join(search_path, "**", "*.csv"), recursive=True)
    
    files = []
    for p in csv_paths:
        path_obj = Path(p)
        try:
            rel = path_obj.relative_to(ROOT)
        except ValueError:
            rel = path_obj
        
        stat = path_obj.stat()
        files.append({
            "name": path_obj.name,
            "relative_path": str(rel),
            "absolute_path": str(path_obj),
            "size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        })
        
    files.sort(key=lambda x: x["name"])
    return files


class IngestRequest(BaseModel):
    csv_path: str


@router.post("/pipeline/ingest")
def start_ingestion(body: IngestRequest):
    import sys
    global _active_process
    if _active_process is not None and _active_process.poll() is None:
        raise HTTPException(status_code=409, detail="Engine is busy. Please wait/stop active simulation first.")
        
    csv_abs = Path(body.csv_path)
    if not csv_abs.is_absolute():
        csv_abs = ROOT / csv_abs
        
    if not csv_abs.exists():
        raise HTTPException(status_code=404, detail=f"CSV file not found: {csv_abs}")

    env = {**os.environ}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "ingest_dataset.py"), "--csv", str(csv_abs)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=env,
        text=True,
        bufsize=1,
    )
    _active_process = proc

    def _stream():
        global _active_process
        try:
            for line in iter(proc.stdout.readline, ""):
                payload = json.dumps({"line": line.rstrip("\n")})
                yield f"data: {payload}\n\n"
            proc.stdout.close()
            proc.wait()
            yield f"data: {json.dumps({'exit_code': proc.returncode})}\n\n"
        finally:
            _active_process = None

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ===================================================================
# 7. Cloud Sync & Control (Supabase PostgreSQL Integration)
# ===================================================================

SUPABASE_CONN_STR = "postgresql://postgres:krishna1156%40db@db.fvfbtxsdmeddzmktbjru.supabase.co:5432/postgres"

# Table list for syncing
SYNC_TABLES = [
    "accounts", "transactions", "account_profiles", "account_relationships",
    "mule_accounts", "mule_networks", "fraud_events", "graph_analytics",
    "system_logs", "simulation_control", "data_source_registry",
    "dataset_accounts", "dataset_features", "dataset_transactions_synthetic"
]

@router.post("/database/cloud/push")
def cloud_push():
    """Wipe cloud tables and push all local data to Supabase."""
    return run_cloud_sync(append=False)

@router.post("/database/cloud/append")
def cloud_append():
    """Append all local data to Supabase without wiping first."""
    return run_cloud_sync(append=True)

@router.post("/database/cloud/delete")
def cloud_delete():
    """Wipe all remote tables on Supabase database."""
    try:
        import psycopg2
        conn = psycopg2.connect(SUPABASE_CONN_STR)
        cur = conn.cursor()
        
        # We try to truncate all SYNC_TABLES if they exist
        for table in SYNC_TABLES:
            try:
                cur.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
            except Exception:
                conn.rollback()
                # Table might not exist, drop or ignore
                try:
                    cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                except Exception:
                    conn.rollback()
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "message": "All remote Supabase tables cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase connection/execution failed: {str(e)}")

@router.post("/database/local/push_delete")
def local_push_delete(body: Optional[DatabaseDeleteRequest] = None):
    """Completely purges all physical database files and deletion logs from disk."""
    files_to_delete = [
        ROOT / "database" / "bank.db",
        ROOT / "database" / "banking.db",
        ROOT / "database" / "ecosystem.db",
        ROOT / "database" / "deletion_log.txt",
        ROOT / "database" / "schema.sql",
        ROOT / "database" / "schema_v2.sql",
    ]
    deleted = []
    failed = []
    for f in files_to_delete:
        if f.exists():
            try:
                f.unlink()
                deleted.append(f.name)
            except Exception as e:
                failed.append(f"{f.name} ({str(e)})")
        else:
            deleted.append(f"{f.name} (not found/already deleted)")
            
    return {
        "success": True,
        "message": "Physical local database files and schema configs completely purged.",
        "deleted": deleted,
        "failed": failed
    }

def run_cloud_sync(append: bool):
    try:
        import psycopg2
        from psycopg2.extras import execute_values
        
        # Connect to Supabase
        pg_conn = psycopg2.connect(SUPABASE_CONN_STR)
        pg_cur = pg_conn.cursor()
        
        # 1. Ensure all Supabase tables exist with PostgreSQL dialect
        ensure_supabase_schema(pg_cur)
        pg_conn.commit()
        
        # 2. Truncate if overwrite
        if not append:
            for table in SYNC_TABLES:
                try:
                    pg_cur.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
                except Exception:
                    pg_conn.rollback()
            pg_conn.commit()
            
        # 3. Read from local SQLite and bulk insert into PostgreSQL
        local_db_path = Path(SQLITE_DB_PATH)
        if not local_db_path.is_absolute():
            local_db_path = ROOT / local_db_path
            
        if not local_db_path.exists():
            pg_cur.close()
            pg_conn.close()
            raise HTTPException(status_code=404, detail=f"Local SQLite database file not found at {local_db_path}")
            
        lite_conn = sqlite3.connect(str(local_db_path))
        lite_conn.row_factory = sqlite3.Row
        lite_cur = lite_conn.cursor()
        
        synced_stats = {}
        
        for table in SYNC_TABLES:
            # Check if table exists in SQLite
            try:
                lite_cur.execute(f'SELECT * FROM "{table}"')
                rows = lite_cur.fetchall()
            except sqlite3.OperationalError:
                # Table does not exist in local SQLite, skip
                continue
                
            if not rows:
                synced_stats[table] = 0
                continue
                
            # Extract column names and prepare execute_values query
            columns = list(rows[0].keys())
            col_placeholders = ", ".join([f'"{c}"' for c in columns])
            
            # Extract values
            data_list = []
            for r in rows:
                data_list.append(tuple(r[c] for c in columns))
                
            # Execute bulk values insert
            insert_query = f'INSERT INTO "{table}" ({col_placeholders}) VALUES %s ON CONFLICT DO NOTHING;'
            
            try:
                execute_values(pg_cur, insert_query, data_list)
                pg_conn.commit()
                synced_stats[table] = len(rows)
            except Exception as e:
                pg_conn.rollback()
                # If ON CONFLICT DO NOTHING fails due to lack of constraint, try regular insert
                try:
                    insert_query_fallback = f'INSERT INTO "{table}" ({col_placeholders}) VALUES %s;'
                    execute_values(pg_cur, insert_query_fallback, data_list)
                    pg_conn.commit()
                    synced_stats[table] = len(rows)
                except Exception as ex:
                    pg_conn.rollback()
                    synced_stats[table] = f"Error: {str(ex)}"
                    
        lite_conn.close()
        pg_cur.close()
        pg_conn.close()
        
        return {
            "success": True,
            "message": "Cloud sync completed.",
            "mode": "append" if append else "overwrite",
            "stats": synced_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

def ensure_supabase_schema(cur):
    # PostgreSQL schema queries
    queries = [
        """
        CREATE TABLE IF NOT EXISTS accounts (
            account_id          TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            age                 INTEGER NOT NULL,
            city                TEXT NOT NULL,
            state               TEXT NOT NULL,
            occupation          TEXT NOT NULL,
            customer_segment    TEXT NOT NULL,
            monthly_income      DOUBLE PRECISION NOT NULL,
            income_range        TEXT NOT NULL,
            account_open_date   TEXT NOT NULL,
            initial_balance     DOUBLE PRECISION NOT NULL,
            balance             DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            risk_profile        TEXT NOT NULL,
            employer            TEXT,
            merchant_category   TEXT,
            cluster_id          TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'ACTIVE',
            activated_at        TEXT,
            created_at          TEXT NOT NULL,
            updated_at          TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id  TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            sender_account  TEXT NOT NULL,
            receiver_account TEXT NOT NULL,
            amount          DOUBLE PRECISION NOT NULL,
            channel         TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'COMPLETED',
            description     TEXT,
            relationship_type TEXT,
            simulated_day   INTEGER DEFAULT 0,
            risk_score      DOUBLE PRECISION DEFAULT 0.0
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS account_profiles (
            account_id          TEXT PRIMARY KEY,
            avg_transaction_amt DOUBLE PRECISION DEFAULT 0.0,
            transaction_count   INTEGER DEFAULT 0,
            last_active         TEXT,
            risk_score          DOUBLE PRECISION DEFAULT 0.0,
            kyc_status          TEXT DEFAULT 'VERIFIED',
            occupation          TEXT,
            monthly_income      DOUBLE PRECISION DEFAULT 0.0
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS account_relationships (
            relationship_id     TEXT PRIMARY KEY,
            source_account      TEXT NOT NULL,
            target_account      TEXT NOT NULL,
            relationship_type   TEXT NOT NULL,
            strength            DOUBLE PRECISION NOT NULL,
            cluster_id          TEXT NOT NULL,
            created_at          TEXT NOT NULL,
            last_seen_at        TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS mule_accounts (
            id              SERIAL PRIMARY KEY,
            account_id      TEXT NOT NULL,
            pattern_type    TEXT NOT NULL,
            chain_id        TEXT NOT NULL,
            layer           INTEGER DEFAULT 0,
            linked_account  TEXT,
            detected_at     TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS mule_networks (
            network_id      TEXT PRIMARY KEY,
            pattern_type    TEXT NOT NULL,
            source_account  TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            active          INTEGER NOT NULL DEFAULT 1
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS fraud_events (
            event_id        TEXT PRIMARY KEY,
            transaction_id  TEXT,
            account_id      TEXT NOT NULL,
            fraud_type      TEXT NOT NULL,
            description     TEXT,
            severity        TEXT DEFAULT 'MEDIUM',
            detected_at     TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS graph_analytics (
            account_id              TEXT PRIMARY KEY,
            pagerank                DOUBLE PRECISION DEFAULT 0.0,
            degree_centrality       DOUBLE PRECISION DEFAULT 0.0,
            betweenness             DOUBLE PRECISION DEFAULT 0.0,
            community_id            TEXT,
            propagated_risk_score   DOUBLE PRECISION DEFAULT 0.0,
            updated_at              TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS system_logs (
            id              SERIAL PRIMARY KEY,
            log_level       TEXT NOT NULL,
            message         TEXT NOT NULL,
            component       TEXT DEFAULT 'COBOL_ENGINE',
            timestamp       TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS simulation_control (
            key             TEXT PRIMARY KEY,
            value           TEXT NOT NULL,
            updated_at      TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS data_source_registry (
            source_id       TEXT PRIMARY KEY,
            source_name     TEXT NOT NULL,
            source_type     TEXT NOT NULL,
            file_path       TEXT,
            row_count       INTEGER DEFAULT 0,
            mule_count      INTEGER DEFAULT 0,
            ingested_at     TEXT,
            is_active       INTEGER DEFAULT 0
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dataset_accounts (
            account_id          TEXT PRIMARY KEY,
            source_row_index    INTEGER NOT NULL,
            account_type        TEXT,
            registration_date   TEXT,
            scheme_code         TEXT,
            region_code         TEXT,
            occupation          TEXT,
            gender              TEXT,
            segment             TEXT,
            f3887_value         INTEGER,
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
            is_mule             INTEGER DEFAULT 0,
            risk_profile        TEXT DEFAULT 'UNKNOWN',
            status              TEXT DEFAULT 'ACTIVE',
            data_source         TEXT DEFAULT 'REGULATORY_FEED',
            ingested_at         TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dataset_features (
            id              SERIAL PRIMARY KEY,
            account_id      TEXT NOT NULL,
            feature_name    TEXT NOT NULL,
            feature_value   DOUBLE PRECISION NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dataset_transactions_synthetic (
            transaction_id      TEXT PRIMARY KEY,
            timestamp           TEXT NOT NULL,
            sender_account      TEXT NOT NULL,
            receiver_account    TEXT NOT NULL,
            amount              DOUBLE PRECISION NOT NULL,
            channel             TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'COMPLETED',
            description         TEXT,
            relationship_type   TEXT,
            simulated_day       INTEGER DEFAULT 0,
            risk_score          DOUBLE PRECISION DEFAULT 0.0,
            data_source         TEXT DEFAULT 'REGULATORY_FEED'
        );
        """
    ]
    for q in queries:
        try:
            cur.execute(q)
        except Exception:
            # Table or column type problem, ignore and log
            pass

