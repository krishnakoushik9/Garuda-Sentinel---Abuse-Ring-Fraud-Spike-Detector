#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import sqlite3
import os
import sys

API_BASE = "http://localhost:8000"
DB_PATH = "./database/ecosystem.db"

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    print("Reading data from SQLite to build request payload...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get a community from graph_analytics
    comm_row = cursor.execute("""
        SELECT community_id, AVG(propagated_risk_score) as avg_risk 
        FROM graph_analytics 
        WHERE community_id IS NOT NULL AND community_id != ''
        GROUP BY community_id 
        ORDER BY avg_risk DESC 
        LIMIT 1
    """).fetchone()

    if not comm_row:
        print("Error: No communities found in graph_analytics table.")
        sys.exit(1)

    community_id = comm_row["community_id"]
    avg_risk = comm_row["avg_risk"]
    print(f"Target Community: {community_id} (Average risk score: {avg_risk:.2f})")

    # Get neighbors (accounts in community)
    cursor.execute("""
        SELECT account_id, name, propagated_risk_score, status 
        FROM graph_analytics 
        LEFT JOIN accounts USING(account_id)
        WHERE community_id = ?
        LIMIT 15
    """, (community_id,))
    
    neighbors = []
    for r in cursor.fetchall():
        neighbors.append({
            "account_id": r["account_id"],
            "name": r["name"] or "Anonymous Account",
            "pagerank": 0.01,
            "risk_score": r["propagated_risk_score"] or 0.5,
            "status": r["status"] or "ACTIVE"
        })

    # Get recent transactions in the community
    account_ids = [n["account_id"] for n in neighbors]
    placeholders = ",".join(["?"] * len(account_ids))
    
    cursor.execute(f"""
        SELECT transaction_id, sender_account, receiver_account, amount, channel, risk_score, timestamp
        FROM transactions
        WHERE sender_account IN ({placeholders}) OR receiver_account IN ({placeholders})
        ORDER BY timestamp DESC
        LIMIT 10
    """, account_ids + account_ids)

    transactions_list = []
    for r in cursor.fetchall():
        transactions_list.append({
            "transaction_id": r["transaction_id"],
            "sender_account": r["sender_account"],
            "receiver_account": r["receiver_account"],
            "amount": r["amount"],
            "channel": r["channel"],
            "risk_score": r["risk_score"] or 0.5,
            "timestamp": r["timestamp"]
        })

    conn.close()

    payload = {
        "risk_score": avg_risk / 100.0 if avg_risk > 1.0 else avg_risk,
        "community": community_id,
        "graph_neighbors": neighbors,
        "recent_transactions": transactions_list,
        "xgboost_features": {
            "dormancy_break_count": len([n for n in neighbors if n["risk_score"] > 0.6]),
            "rapid_fan_out_flag": 1 if len(transactions_list) > 5 else 0,
            "mule_sequence_score": 0.88,
            "avg_amount_zscore": 2.35,
            "amount_lakhs": str(round(sum(t["amount"] for t in transactions_list) / 100000.0, 2))
        },
        "lstm_score": 0.91,
        "gnn_score": avg_risk / 100.0 if avg_risk > 1.0 else avg_risk
    }

    url = f"{API_BASE}/api/v1/agent-investigation/investigate"
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, method="POST")
    req.add_header("Content-Type", "application/json")

    print(f"Triggering investigation for community {community_id} via API...")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            status = response.status
            body = response.read().decode('utf-8')
            resp_json = json.loads(body)
            print(f"Response Status: {status}")
            print("\n==================================================")
            print("                 AGENT INVESTIGATION REPORT")
            print("==================================================")
            print(resp_json.get("report", "No report generated."))
            print("==================================================")
            print(f"PDF Download URL: {resp_json.get('pdf_download_url')}")
            print(f"Rate Limit Remaining: {resp_json.get('rate_limit_remaining')}")
            print("==================================================")
    except Exception as e:
        print(f"Error calling investigation API: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))

if __name__ == "__main__":
    main()
