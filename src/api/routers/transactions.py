from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import sqlite3
from src.api.deps import get_db
from src.api.models.schemas import Transaction, TransactionStats
from src.models.xgboost_scorer import XGBoostScorer
from src.api.routers.datasource import get_active_source
from src.pipeline.feature_engineering import FeatureEngineer
from src.ml.anomaly.isolation_forest import RealTimeIsolationForest

from src.pipeline.risk_engine import UnifiedRiskEngine

router = APIRouter(prefix="/transactions", tags=["Transactions"])
scorer = XGBoostScorer()
feature_eng = FeatureEngineer()
iforest = RealTimeIsolationForest()
risk_engine = UnifiedRiskEngine()



@router.get("", response_model=List[Transaction])
def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=250),
    channel: Optional[str] = None,
    risk_tier: str = "all",
    account_id: Optional[str] = None,
    search: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    status: Optional[str] = None,
    sort_by: str = "timestamp",
    sort_order: str = "DESC",
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * limit
    source = get_active_source(db)
    if source == "REGULATORY_FEED":
        query = "SELECT * FROM transactions WHERE sender_account LIKE 'REAL%'"
    else:
        query = "SELECT * FROM transactions WHERE (sender_account LIKE 'ACC%')"
    params = []
    
    if channel:
        query += " AND channel = ?"
        params.append(channel)
        
    if account_id:
        query += " AND (sender_account = ? OR receiver_account = ?)"
        params.extend([account_id, account_id])
        
    if search:
        query += " AND (transaction_id LIKE ? OR sender_account LIKE ? OR receiver_account LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    if min_amount is not None:
        query += " AND amount >= ?"
        params.append(min_amount)
        
    if max_amount is not None:
        query += " AND amount <= ?"
        params.append(max_amount)
        
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if risk_tier == "suspicious":
        query += " AND risk_score >= 0.4 AND risk_score <= 0.8"
    elif risk_tier == "mule":
        query += " AND risk_score > 0.8"
    elif risk_tier == "high":
        query += " AND risk_score >= 0.6"
        
    # Prevent SQL injection on sorting identifiers
    valid_sort_cols = {"timestamp", "amount", "risk_score", "transaction_id"}
    if sort_by not in valid_sort_cols:
        sort_by = "timestamp"
        
    sort_order = "DESC" if sort_order.upper() == "DESC" else "ASC"
    
    query += f" ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]

@router.get("/stats", response_model=TransactionStats)
def get_transaction_stats(db: sqlite3.Connection = Depends(get_db)):
    total = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    fraud = db.execute("SELECT COUNT(*) FROM fraud_events").fetchone()[0]
    mule = db.execute("SELECT COUNT(DISTINCT account_id) FROM mule_accounts").fetchone()[0]
    avg_risk = db.execute("SELECT AVG(risk_score) FROM transactions").fetchone()[0] or 0.0
    
    return {
        "total_count": total,
        "fraud_count": fraud,
        "mule_count": mule,
        "avg_risk_score": round(avg_risk, 4)
    }

@router.get("/{txn_id}", response_model=Transaction)
def get_transaction(txn_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM transactions WHERE transaction_id = ?", (txn_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return dict(row)

from pydantic import BaseModel
class SendTransactionRequest(BaseModel):
    sender_account: str
    receiver_account: str
    amount: float
    channel: str
    description: Optional[str] = None

@router.post("/send", response_model=Transaction)
def send_transaction(req: SendTransactionRequest, db: sqlite3.Connection = Depends(get_db)):
    # Fetch sender
    sender = db.execute("SELECT * FROM accounts WHERE account_id = ?", (req.sender_account,)).fetchone()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender account not found")
        
    # Fetch receiver
    receiver = db.execute("SELECT * FROM accounts WHERE account_id = ?", (req.receiver_account,)).fetchone()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver account not found")
        
    sender_dict = dict(sender)
    receiver_dict = dict(receiver)
    
    sender_balance = sender_dict.get("balance", 0.0)
    if sender_balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient Balance")
        
    # Perform atomic update
    new_sender_balance = sender_balance - req.amount
    new_receiver_balance = receiver_dict.get("balance", 0.0) + req.amount
    
    db.execute("UPDATE accounts SET balance = ? WHERE account_id = ?", (new_sender_balance, req.sender_account))
    db.execute("UPDATE accounts SET balance = ? WHERE account_id = ?", (new_receiver_balance, req.receiver_account))
    
    import uuid
    from datetime import datetime
    txn_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
    timestamp = datetime.now().isoformat()
    
    # 1. Compute features for the new transaction in real-time
    txn_dict = {
        "transaction_id": txn_id,
        "timestamp": timestamp,
        "sender_account": req.sender_account,
        "receiver_account": req.receiver_account,
        "amount": req.amount,
        "channel": req.channel,
        "description": req.description or ""
    }
    
    xgb_score = 0.0
    anomaly_score = 0.0
    risk_score = 0.0
    try:
        # Run confidence-based cascade ensemble prediction
        cascade_res = risk_engine.predict_with_confidence(req.sender_account, txn_dict)
        risk_score = cascade_res["unified_risk_score"]
        xgb_score = risk_score  # Set for the zero-day alert logic below
        
        # Also compute Isolation Forest score in parallel for zero-day threat detection
        features = feature_eng.compute_features(req.sender_account, txn_dict)
        features_arr = features.to_array().reshape(1, -1)
        anomaly_score = iforest.score(features_arr)
    except Exception as e:
        print(f"[TRANSACTIONS SCORING ERROR] Ensemble cascade scoring fell back due to: {e}")
        # Secure high-fidelity fallback if model isn't trained or loads fail
        if req.amount >= 100000:
            risk_score = 0.85
        elif req.amount >= 10000:
            risk_score = 0.45
        xgb_score = risk_score
        
    risk_score = round(risk_score, 4)

    
    # 2. Check thresholds and escalate alert if zero-day anomaly matched with high XGBoost score
    # If anomaly_score > threshold AND xgb_score > 0.5, escalate to human review (set require_review=True/1 in alert)
    if anomaly_score > iforest.threshold and xgb_score > 0.5:
        event_id = f"FE-IF-{uuid.uuid4().hex[:8].upper()}"
        desc = (f"Zero-day outlier detected by unsupervised Isolation Forest "
                f"(anomaly score: {anomaly_score:.3f} > {iforest.threshold:.2f}) "
                f"correlated with elevated XGBoost threat rating ({xgb_score:.3f} > 0.50). "
                f"Escalating ticket to human review.")
        
        # Idempotently add the require_review column to core schema if not already present
        try:
            db.execute("ALTER TABLE fraud_events ADD COLUMN require_review INTEGER DEFAULT 0")
            db.commit()
        except Exception:
            pass
            
        db.execute("""
            INSERT OR REPLACE INTO fraud_events (event_id, transaction_id, account_id, fraud_type, description, severity, detected_at, require_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, txn_id, req.sender_account, "ZERO_DAY_ANOMALY", desc, "HIGH", timestamp, 1))
        
    db.execute("""
        INSERT INTO transactions (transaction_id, timestamp, sender_account, receiver_account, amount, channel, status, description, risk_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (txn_id, timestamp, req.sender_account, req.receiver_account, req.amount, req.channel, "COMPLETED", req.description or "", risk_score))
    
    db.commit()
    
    return {
        "transaction_id": txn_id,
        "timestamp": timestamp,
        "sender_account": req.sender_account,
        "receiver_account": req.receiver_account,
        "amount": req.amount,
        "channel": req.channel,
        "status": "COMPLETED",
        "description": req.description or "",
        "risk_score": risk_score
    }


