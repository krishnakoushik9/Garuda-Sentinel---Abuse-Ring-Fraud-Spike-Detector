import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from evidently import Report
from evidently.presets import DataDriftPreset

from src.config import SQLITE_DB_PATH
from src.pipeline.feature_engineering import FeatureEngineer

# Resolve Paths
ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

def fetch_transactions_for_drift(target_date_str=None):
    """
    Fetches reference transactions (prior to target_date_str) and current transactions (on target_date_str).
    If target_date_str is None, uses the date of the latest transaction in the database.
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        if not target_date_str:
            # Find the latest date in the transactions table
            row = cursor.execute("SELECT date(timestamp) FROM transactions ORDER BY timestamp DESC LIMIT 1").fetchone()
            if not row:
                raise ValueError("No transactions found in database.")
            target_date_str = row[0]
            
        print(f"[DRIFT] Target date for drift detection: {target_date_str}")
        
        # Fetch current day's transactions (max 1000)
        curr_rows = cursor.execute(
            "SELECT * FROM transactions WHERE date(timestamp) = ? ORDER BY timestamp DESC LIMIT 1000",
            (target_date_str,)
        ).fetchall()
        
        if len(curr_rows) == 0:
            print(f"[DRIFT] No transactions found on {target_date_str}. Using the latest 300 transactions as current.")
            curr_rows = cursor.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 300"
            ).fetchall()
            if curr_rows:
                target_date_str = curr_rows[0]['timestamp'][:10]
        
        # Fetch reference transactions: prior to target date (max 2000)
        ref_rows = cursor.execute(
            "SELECT * FROM transactions WHERE date(timestamp) < ? ORDER BY timestamp DESC LIMIT 2000",
            (target_date_str,)
        ).fetchall()
        
        # Fallback if there's no history prior to the first transaction
        if len(ref_rows) < 50:
            print("[DRIFT] Not enough history prior to target date. Using a subset of older transactions as reference.")
            ref_rows = cursor.execute(
                "SELECT * FROM transactions ORDER BY timestamp ASC LIMIT 1000"
            ).fetchall()
            
        current_txs = [dict(r) for r in curr_rows]
        reference_txs = [dict(r) for r in ref_rows]
        
        return target_date_str, current_txs, reference_txs
    finally:
        conn.close()

def compute_dataset_features(txs):
    """
    Runs the pipeline's feature engineer to calculate model features for a list of transactions.
    """
    fe = FeatureEngineer()
    X = []
    for tx in txs:
        try:
            # Compute features for the sender account based on this transaction
            feats = fe.compute_features(tx['sender_account'], tx)
            X.append(feats.to_array())
        except Exception as e:
            continue
            
    columns = [
        'amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag',
        'night_txn_ratio', 'txn_velocity_1h', 'txn_velocity_24h', 'txn_velocity_7d',
        'unique_beneficiaries_7d', 'graph_degree_centrality', 'suspicious_neighbor_count', 'hop_2_mule_count'
    ]
    return pd.DataFrame(X, columns=columns)

def trigger_drift_alert(target_date, drift_share, drifted_features):
    """
    Inserts a critical system event into SQLite's fraud_events table to alert the SSE stream.
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        event_id = f"FE-DRIFT-{target_date}"
        desc = (
            f"SYSTEM ALERT: Significant training/inference data drift detected for date {target_date}. "
            f"Drift share: {drift_share:.1%} of features changed (Threshold: 20%). "
            f"Drifted features: {', '.join(drifted_features)}"
        )
        
        conn.execute("""
            INSERT OR REPLACE INTO fraud_events 
            (event_id, transaction_id, account_id, fraud_type, description, severity, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            "N/A",
            "SYSTEM",
            "DATA_DRIFT",
            desc,
            "CRITICAL",
            datetime.now().isoformat()
        ))
        conn.commit()
        print(f"[DRIFT] Drift alert triggered in core ledger: {event_id}")
    except Exception as e:
        print(f"[DRIFT] Error writing drift alert to SQLite: {e}")
    finally:
        conn.close()

def run_drift_detection(target_date_str=None, threshold=0.20):
    """
    Runs the daily data drift report, writes the summary JSON to disk, and triggers alerts if needed.
    """
    print("\n=== Data Drift Detection Service ===")
    target_date, current_txs, reference_txs = fetch_transactions_for_drift(target_date_str)
    
    print(f"[DRIFT] Reference Size: {len(reference_txs)} transactions")
    print(f"[DRIFT] Current Size: {len(current_txs)} transactions")
    
    if not current_txs or not reference_txs:
        print("[DRIFT] Error: Empty dataset(s). Cannot run drift detection.")
        return
        
    print("[DRIFT] Computing feature vectors for reference dataset...")
    ref_df = compute_dataset_features(reference_txs)
    
    print("[DRIFT] Computing feature vectors for current dataset...")
    curr_df = compute_dataset_features(current_txs)
    
    if ref_df.empty or curr_df.empty:
        print("[DRIFT] Error: Feature vectors dataframe is empty.")
        return
        
    print("[DRIFT] Generating Evidently Data Drift snapshot...")
    report = Report([DataDriftPreset()])
    snapshot = report.run(current_data=curr_df, reference_data=ref_df)
    
    # Save full JSON log report
    json_path = LOGS_DIR / f"drift_report_{target_date}.json"
    snapshot.save_json(str(json_path))
    print(f"[DRIFT] Evidently JSON report saved to {json_path}")
    
    # Parse metrics
    drift_share = 0.0
    drift_count = 0
    drifted_features = []
    
    for k, val in snapshot.metric_results.items():
        sd = val.to_dict()
        metric_name = sd.get('metric_name', '')
        config = sd.get('config', {})
        val_data = sd.get('value')
        
        if 'DriftedColumnsCount' in metric_name or (isinstance(val_data, dict) and 'share' in val_data):
            drift_share = val_data['share']
            drift_count = val_data['count']
        elif 'ValueDrift' in metric_name or config.get('type') == 'evidently:metric_v2:ValueDrift':
            col = config.get('column')
            p_val = val_data
            col_threshold = config.get('threshold', 0.05)
            if col and p_val < col_threshold:
                drifted_features.append(col)
                
    print(f"[DRIFT] Drifted columns count: {drift_count}/{len(ref_df.columns)}")
    print(f"[DRIFT] Drifted columns share: {drift_share:.2%}")
    print(f"[DRIFT] Drifted features: {drifted_features}")
    
    # Check threshold and trigger alert
    if drift_share >= threshold:
        trigger_drift_alert(target_date, drift_share, drifted_features)
    else:
        print("[DRIFT] Success: Drift level is safe.")

if __name__ == "__main__":
    run_drift_detection()
