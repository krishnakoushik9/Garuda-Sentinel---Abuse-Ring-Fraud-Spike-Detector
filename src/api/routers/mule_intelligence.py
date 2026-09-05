from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import sqlite3
import os
import subprocess
import threading
import time

from src.config import SQLITE_DB_PATH
from src.mule_intelligence.patterns import MulePatternEvaluator
from src.mule_intelligence.money_flow_tracer import MoneyFlowTracer
from src.mule_intelligence.network_scorer import NetworkRiskPropagator
from src.mule_intelligence.early_warning import EarlyWarningSystem

router = APIRouter(prefix="/mule", tags=["Mule Intelligence"])

@router.get("/patterns/{account_id}", response_model=Dict[str, Any])
def get_mule_patterns(account_id: str):
    """
    Evaluates and returns all 8 distinct mule pattern indicators for a specific account.
    """
    evaluator = MulePatternEvaluator()
    try:
        # Verify account exists in SQLite
        conn = sqlite3.connect(SQLITE_DB_PATH)
        row = conn.execute("SELECT 1 FROM accounts WHERE account_id = ?", (account_id,)).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail=f"Suspect account {account_id} not found in repository.")
            
        evaluation = evaluator.evaluate_account(account_id)
        triggered_count = sum(1 for p in evaluation.values() if p["triggered"])
        
        return {
            "account_id": account_id,
            "triggered_patterns_count": triggered_count,
            "patterns": evaluation
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate mule patterns: {e}")

@router.get("/trace/{account_id}/downstream", response_model=Dict[str, Any])
def trace_downstream_flow(account_id: str, max_hops: int = Query(6, ge=1, le=10)):
    """
    Traces downstream fund transfers to detect cascading relays and terminal cash-out terminals.
    """
    tracer = MoneyFlowTracer()
    try:
        flow = tracer.trace_downstream(account_id, max_hops=max_hops)
        narrative = tracer.generate_flow_summary(flow)
        return {
            "account_id": account_id,
            "trace_type": "DOWNSTREAM_FLOW",
            "narrative": narrative,
            "flow_graph": flow
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Downstream money flow tracing failed: {e}")

@router.get("/trace/{account_id}/upstream", response_model=Dict[str, Any])
def trace_upstream_flow(account_id: str, max_hops: int = Query(4, ge=1, le=8)):
    """
    Traces incoming deposits backwards to find original scam/mule seed nodes.
    """
    tracer = MoneyFlowTracer()
    try:
        flow = tracer.trace_upstream(account_id, max_hops=max_hops)
        return {
            "account_id": account_id,
            "trace_type": "UPSTREAM_FLOW",
            "flow_graph": flow
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upstream money flow tracing failed: {e}")

@router.get("/network-risk", response_model=List[Dict[str, Any]])
def get_network_risk():
    """
    Calculates contagion threat scores by propagating risk from known flagged accounts.
    Returns the top 50 elevated risk profiles in the network.
    """
    propagator = NetworkRiskPropagator()
    try:
        # Seed known mules from SQLite
        conn = sqlite3.connect(SQLITE_DB_PATH)
        rows = conn.execute(
            "SELECT account_id FROM accounts WHERE status IN ('GOVT_FLAGGED', 'RFA') LIMIT 25"
        ).fetchall()
        conn.close()
        
        mules = [r[0] for r in rows]
        if not mules:
            # Fallback to general high-risk accounts if database is fresh
            conn = sqlite3.connect(SQLITE_DB_PATH)
            rows = conn.execute("SELECT account_id FROM accounts LIMIT 10").fetchall()
            conn.close()
            mules = [r[0] for r in rows]
            
        risk_scores = propagator.propagate_risk(mules)
        
        # Sort and take top 50
        sorted_risk = sorted(risk_scores.items(), key=lambda x: x[1], reverse=True)[:50]
        
        results = []
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        for aid, score in sorted_risk:
            acc = conn.execute("SELECT name, risk_profile, status FROM accounts WHERE account_id = ?", (aid,)).fetchone()
            results.append({
                "account_id": aid,
                "propagated_risk_score": score,
                "name": acc["name"] if acc else "Unknown Contact",
                "risk_profile": acc["risk_profile"] if acc else "HIGH",
                "status": acc["status"] if acc else "ACTIVE"
            })
        conn.close()
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Network risk propagation failed: {e}")

@router.get("/ews/alerts", response_model=List[Dict[str, Any]])
def get_ews_alerts():
    """
    Fetches hot Early Warning Signal (EWS) triggers showing score threat > 0.6.
    """
    ews = EarlyWarningSystem()
    try:
        alerts = ews.run_batch_ews_scan(limit=100)
        # Filter for action required
        actionable = [a for a in alerts if a["ews_score"] >= 0.6]
        return actionable
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EWS alerts extraction failed: {e}")

@router.post("/ews/scan", response_model=Dict[str, Any])
def trigger_ews_scan(limit: int = Query(100, ge=10, le=500)):
    """
    Triggers a fresh batch scan of accounts for early-warning signals.
    """
    ews = EarlyWarningSystem()
    try:
        alerts = ews.run_batch_ews_scan(limit=limit)
        triggered_count = sum(1 for a in alerts if a["ews_score"] >= 0.6)
        return {
            "status": "success",
            "accounts_scanned": len(alerts),
            "actionable_alerts_count": triggered_count,
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch EWS scan run failed: {e}")

@router.get("/contamination/{account_id}", response_model=Dict[str, Any])
def get_contamination_radius(account_id: str):
    """
    Evaluates the threat contamination radius (hop counts) centered at a suspected mule node.
    """
    propagator = NetworkRiskPropagator()
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        row = conn.execute("SELECT 1 FROM accounts WHERE account_id = ?", (account_id,)).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail=f"Suspect account {account_id} not found in repository.")
            
        radius = propagator.get_contamination_radius(account_id)
        return radius
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contamination radius lookup failed: {e}")

from pydantic import BaseModel

class TrainRequest(BaseModel):
    limit: Optional[int] = None
    device: Optional[str] = "cpu"

# In-memory training status tracker
training_state = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "logs": [],
    "error": None
}

def run_training_subprocess(limit: Optional[int] = None, device: Optional[str] = "cpu"):
    global training_state
    training_state["status"] = "training"
    training_state["started_at"] = time.time()
    training_state["finished_at"] = None
    training_state["logs"] = []
    training_state["error"] = None
    
    try:
        # Use python from the virtualenv
        python_bin = ".venv/bin/python"
        
        # Prepare environment
        subprocess_env = {
            "PYTHONPATH": ".",
            "TRAIN_TRANSACTION_LIMIT": str(limit) if limit is not None else "",
            "TRAIN_DEVICE": device or "cpu",
            **os.environ
        }
        
        process = subprocess.Popen(
            [python_bin, "-u", "scripts/train_models.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=subprocess_env
        )
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            # Append line to logs
            training_state["logs"].append(line.strip())
            # Keep enough history for full-database training progress logs.
            if len(training_state["logs"]) > 1000:
                training_state["logs"].pop(0)
                
        process.wait()
        if process.returncode == 0:
            training_state["status"] = "completed"
        else:
            training_state["status"] = "failed"
            training_state["error"] = f"Exit code {process.returncode}"
    except Exception as e:
        training_state["status"] = "failed"
        training_state["error"] = str(e)
    finally:
        training_state["finished_at"] = time.time()

@router.post("/models/train", response_model=Dict[str, Any])
def trigger_model_training(req: Optional[TrainRequest] = None):
    """
    Triggers a background task to retrain the XGBoost, GraphSAGE, and LSTM Autoencoder models.
    """
    global training_state
    if training_state["status"] == "training":
        return {
            "status": "training",
            "message": "Training already in progress",
            "started_at": training_state["started_at"]
        }
        
    limit = req.limit if req else None
    device = req.device if req else "cpu"
    
    # Start thread
    thread = threading.Thread(target=run_training_subprocess, args=(limit, device))
    thread.daemon = True
    thread.start()
    
    return {
        "status": "training",
        "message": "Training initiated successfully in background task",
        "started_at": time.time()
    }

@router.get("/models/status", response_model=Dict[str, Any])
def get_model_training_status():
    """
    Fetches the current status and real-time logs of the machine learning training pipeline.
    """
    global training_state
    return training_state
