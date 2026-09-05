from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import uuid
import sqlite3
import json
import os
from src.api.models.schemas import InvestigationResult
from src.agents.orchestrator import FraudOrchestrator
from src.api.deps import get_db
from src.config import SQLITE_DB_PATH

router = APIRouter(prefix="/investigate", tags=["Investigations"])
orchestrator = FraudOrchestrator()

# Create table on startup if not exists
def init_investigations_db():
    db_dir = os.path.dirname(SQLITE_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                account_id TEXT,
                status TEXT,
                result JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

init_investigations_db()

@router.post("", response_model=Dict[str, str])
def start_investigation(
    txn_id: str, 
    account_id: str, 
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_db)
):
    inv_id = str(uuid.uuid4())
    
    # Store initial state in SQLite
    db.execute(
        "INSERT INTO investigations (id, account_id, status, result) VALUES (?, ?, ?, ?)",
        (inv_id, account_id, "processing", json.dumps({"txn_id": txn_id}))
    )
    db.commit()
    
    # Fetch features from DB (simplified)
    row = db.execute("SELECT * FROM transactions WHERE transaction_id = ?", (txn_id,)).fetchone()
    features = dict(row) if row else {}
    
    def run_task():
        # Open separate connection for background thread
        conn = sqlite3.connect(SQLITE_DB_PATH)
        try:
            result = orchestrator.run_investigation(txn_id, account_id, features)
            conn.execute(
                "UPDATE investigations SET status = ?, result = ? WHERE id = ?",
                ("completed", json.dumps(result), inv_id)
            )
            conn.commit()
        except Exception as e:
            conn.execute(
                "UPDATE investigations SET status = ?, result = ? WHERE id = ?",
                ("failed", json.dumps({"error": str(e)}), inv_id)
            )
            conn.commit()
        finally:
            conn.close()

    background_tasks.add_task(run_task)
    return {"investigation_id": inv_id}

@router.get("/{investigation_id}", response_model=Dict[str, Any])
def get_investigation(investigation_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM investigations WHERE id = ?", (investigation_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    data = dict(row)
    result_str = data.get("result")
    if result_str:
        try:
            result_dict = json.loads(result_str)
        except Exception:
            result_dict = {}
    else:
        result_dict = {}
        
    merged = {
        "id": data["id"],
        "account_id": data["account_id"],
        "status": data["status"],
        "created_at": data["created_at"],
        **result_dict
    }
    return merged

@router.get("", response_model=List[Dict[str, Any]])
def list_investigations(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM investigations ORDER BY created_at DESC").fetchall()
    results = []
    for row in rows:
        data = dict(row)
        result_str = data.get("result")
        if result_str:
            try:
                result_dict = json.loads(result_str)
            except Exception:
                result_dict = {}
        else:
            result_dict = {}
            
        merged = {
            "id": data["id"],
            "account_id": data["account_id"],
            "status": data["status"],
            "created_at": data["created_at"],
            **result_dict
        }
        results.append(merged)
    return results
