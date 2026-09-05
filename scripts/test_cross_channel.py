#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import sqlite3
import sys
from src.config import SQLITE_DB_PATH

API_BASE = "http://localhost:8000/api/v1/cross-channel"

def print_result(name, success, info=""):
    color = "\033[92m[PASS]\033[0m" if success else "\033[91m[FAIL]\033[0m"
    print(f"{color} {name:<50} {info}")

def run_test(path, method="GET", data=None):
    url = f"{API_BASE}{path}"
    req_data = None
    if data:
        if method == "POST":
            req_data = json.dumps(data).encode('utf-8')
        else:
            url += "?" + urllib.parse.urlencode(data)
            
    req = urllib.request.Request(url, data=req_data, method=method)
    if req_data:
        req.add_header("Content-Type", "application/json")
        
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode('utf-8')
            return response.status, json.loads(body) if body else {}
    except Exception as e:
        return 500, {"error": str(e)}

def main():
    print("==================================================")
    print("      PS2 CROSS-CHANNEL INTEGRATION SMOKE TEST")
    print("==================================================")
    
    # 0. Get a real active account from SQLite
    conn = sqlite3.connect(SQLITE_DB_PATH)
    row = conn.execute("SELECT account_id FROM accounts LIMIT 1").fetchone()
    conn.close()
    
    if not row:
        print("\033[91mNo accounts found in SQLite! Please run banking COBOL engine first.\033[0m")
        sys.exit(1)
        
    test_account = row[0]
    print(f"Using suspect account for testing: {test_account}\n")
    
    all_passed = True

    # 1. GET /cross-channel/profile/{account_id}
    status, res = run_test(f"/profile/{test_account}")
    if status == 200:
        profile = res.get("profile", {})
        dom = profile.get("dominant_channel", "None")
        div = profile.get("channel_diversity_score", 0.0)
        print_result("Channel Profile Breakdown (GET /profile/{id})", True, f"Dominant: {dom}, Diversity: {div}")
    else:
        all_passed = False
        print_result("Channel Profile Breakdown (GET /profile/{id})", False, f"Status: {status}")

    # 2. GET /cross-channel/hop-alerts
    status, hops = run_test("/hop-alerts")
    if status == 200 and isinstance(hops, list):
        print_result("Channel Hop Detector (GET /hop-alerts)", True, f"Found {len(hops)} active hopping breaches.")
    else:
        all_passed = False
        print_result("Channel Hop Detector (GET /hop-alerts)", False, f"Status: {status}")

    # 3. GET /cross-channel/inter-bank
    status, ib = run_test("/inter-bank")
    if status == 200:
        alert = ib.get("inter_bank_alert", {})
        npci_count = len(ib.get("npci_blacklisted_vpas", []))
        print_result("Inter-Bank Signals Ingestion (GET /inter-bank)", True, f"NPCI caution records received: {npci_count}")
    else:
        all_passed = False
        print_result("Inter-Bank Signals Ingestion (GET /inter-bank)", False, f"Status: {status}")

    # 4. GET /cross-channel/unified-score/{account_id}
    status, score = run_test(f"/unified-score/{test_account}")
    if status == 200:
        val = score.get("unified_risk_score", 0.0)
        tier = score.get("risk_tier", "LOW")
        act = score.get("action", "ALLOW")
        t3_run = score.get("executed_tier_3", False)
        print_result("Unified Risk Engine (GET /unified-score/{id})", True, f"Score: {val} ({tier}), Action: {act}, Tier 3 Deep Scan: {t3_run}")
    else:
        all_passed = False
        print_result("Unified Risk Engine (GET /unified-score/{id})", False, f"Status: {status}")

    # 5. POST /cross-channel/simulate-feed
    status, feed = run_test("/simulate-feed", "POST")
    if status == 200:
        npci_cnt = feed.get("processed_alerts", {}).get("npci_vpas_blocked_count", 0)
        print_result("Feed Simulation Trigger (POST /simulate-feed)", True, f"Caution flagged {npci_cnt} matched accounts.")
    else:
        all_passed = False
        print_result("Feed Simulation Trigger (POST /simulate-feed)", False, f"Status: {status}")

    print("\n==================================================")
    if all_passed:
        print("\033[92mALL CROSS-CHANNEL INTEGRATION ENDPOINTS ARE PASS\033[0m")
        sys.exit(0)
    else:
        print("\033[91mCROSS-CHANNEL INTEGRATION SMOKE TEST FAILED\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
