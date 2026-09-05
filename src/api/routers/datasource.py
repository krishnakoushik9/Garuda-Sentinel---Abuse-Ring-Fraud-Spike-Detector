"""Data source status and switching endpoint."""
from fastapi import APIRouter, Depends
import sqlite3
from datetime import datetime
from src.api.deps import get_db

router = APIRouter(prefix="/datasource", tags=["Data Source"])


def get_active_source(db: sqlite3.Connection) -> str:
    """Returns 'COBOL_SYNTHETIC' or 'REGULATORY_FEED' based on simulation_control."""
    row = db.execute(
        "SELECT value FROM simulation_control WHERE key = 'data_source'"
    ).fetchone()
    if row:
        return row[0]
    return "COBOL_SYNTHETIC"


@router.get("/status")
def datasource_status(db: sqlite3.Connection = Depends(get_db)):
    active = get_active_source(db)

    cobol_accounts = db.execute(
        "SELECT COUNT(*) FROM accounts WHERE account_id LIKE 'ACC%'"
    ).fetchone()[0]

    real_accounts = 0
    real_mules = 0
    try:
        real_accounts = db.execute("SELECT COUNT(*) FROM dataset_accounts").fetchone()[0]
        real_mules = db.execute(
            "SELECT COUNT(*) FROM dataset_accounts WHERE is_mule = 1"
        ).fetchone()[0]
    except Exception:
        pass

    # Last switched timestamp
    row = db.execute(
        "SELECT updated_at FROM simulation_control WHERE key = 'data_source'"
    ).fetchone()
    last_switched = row[0] if row else None

    return {
        "active_source": active,
        "cobol_accounts": cobol_accounts,
        "real_accounts": real_accounts,
        "real_mules": real_mules,
        "last_switched": last_switched,
    }


from pydantic import BaseModel

class DataSourceSwitchRequest(BaseModel):
    source: str  # 'COBOL_SYNTHETIC' or 'REGULATORY_FEED'


@router.post("/switch")
def datasource_switch(body: DataSourceSwitchRequest, db: sqlite3.Connection = Depends(get_db)):
    source = body.source
    if source not in {"COBOL_SYNTHETIC", "REGULATORY_FEED"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid source. Must be 'COBOL_SYNTHETIC' or 'REGULATORY_FEED'")

    now = datetime.now().isoformat(timespec="seconds")
    
    try:
        db.execute("UPDATE data_source_registry SET is_active = 0")
        db.execute(
            "UPDATE data_source_registry SET is_active = 1 WHERE source_type = ?",
            (source,)
        )
    except sqlite3.OperationalError:
        pass

    for key, val in [
        ("data_source", source),
        ("status", "finished"),
    ]:
        db.execute(
            "INSERT OR REPLACE INTO simulation_control (key, value, updated_at) VALUES (?,?,?)",
            (key, val, now),
        )

    db.commit()
    
    return {
        "status": "success",
        "active_source": source,
        "last_switched": now
    }
