#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import sqlite3
import sys
from src.config import SQLITE_DB_PATH

API_BASE = "http://localhost:8000/api/v1/mule"

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
    print("      PS2 MULE DETECTION INTELLIGENCE SMOKE TEST")
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

    # 1. GET /mule/patterns/{account_id}
    status, patterns = run_test(f"/patterns/{test_account}")
    if status == 200:
        triggered = patterns.get("triggered_patterns_count", 0)
        print_result("Mule Patterns Evaluator (GET /patterns/{id})", True, f"Triggered: {triggered}/8 patterns.")
    else:
        all_passed = False
        print_result("Mule Patterns Evaluator (GET /patterns/{id})", False, f"Status: {status}, Error: {patterns.get('error')}")

    # 2. GET /mule/trace/{account_id}/downstream
    status, ds = run_test(f"/trace/{test_account}/downstream")
    if status == 200:
        flow = ds.get("flow_graph", {})
        nodes = len(flow.get("nodes", []))
        edges = len(flow.get("edges", []))
        total_traced = ds.get("flow_graph", {}).get("total_amount_traced", 0.0)
        print_result("Downstream Flow Tracer (GET /trace/{id}/downstream)", True, f"Traced {nodes} nodes, {edges} flow paths. Total: ₹{total_traced:,.2f}")
    else:
        all_passed = False
        print_result("Downstream Flow Tracer (GET /trace/{id}/downstream)", False, f"Status: {status}")

    # 3. GET /mule/trace/{account_id}/upstream
    status, us = run_test(f"/trace/{test_account}/upstream")
    if status == 200:
        flow = us.get("flow_graph", {})
        nodes = len(flow.get("nodes", []))
        edges = len(flow.get("edges", []))
        print_result("Upstream Flow Tracer (GET /trace/{id}/upstream)", True, f"Traced {nodes} nodes, {edges} flow paths back to source.")
    else:
        all_passed = False
        print_result("Upstream Flow Tracer (GET /trace/{id}/upstream)", False, f"Status: {status}")

    # 4. GET /mule/network-risk
    status, nr = run_test("/network-risk")
    if status == 200 and isinstance(nr, list):
        print_result("Network Risk Contagion Scorer (GET /network-risk)", True, f"Fetched top {len(nr)} infected accounts.")
    else:
        all_passed = False
        print_result("Network Risk Contagion Scorer (GET /network-risk)", False, f"Status: {status}")

    # 5. GET /mule/ews/alerts
    status, ews = run_test("/ews/alerts")
    if status == 200 and isinstance(ews, list):
        print_result("EWS Active Alerts Fetcher (GET /ews/alerts)", True, f"Fetched {len(ews)} active EWS alerts.")
    else:
        all_passed = False
        print_result("EWS Active Alerts Fetcher (GET /ews/alerts)", False, f"Status: {status}")

    # 6. POST /mule/ews/scan
    status, scan = run_test("/ews/scan", "POST")
    if status == 200:
        scanned = scan.get("accounts_scanned", 0)
        actionable = scan.get("actionable_alerts_count", 0)
        print_result("EWS Batch Scan Trigger (POST /ews/scan)", True, f"Scanned {scanned} accounts, found {actionable} actionable pre-mules.")
    else:
        all_passed = False
        print_result("EWS Batch Scan Trigger (POST /ews/scan)", False, f"Status: {status}")

    # 7. GET /mule/contamination/{account_id}
    status, cont = run_test(f"/contamination/{test_account}")
    if status == 200:
        radius = cont.get("total_threat_radius", 0)
        print_result("Contamination Radius Evaluator (GET /contamination/{id})", True, f"Suspect node threat propagation radius: {radius} accounts.")
    else:
        all_passed = False
        print_result("Contamination Radius Evaluator (GET /contamination/{id})", False, f"Status: {status}")

    print("\n==================================================")
    if all_passed:
        print("\033[92mALL MULE INTELLIGENCE ENDPOINTS ARE FUNCTIONAL // PASS\033[0m")
        sys.exit(0)
    else:
        print("\033[91mMULE INTELLIGENCE SMOKE TEST FAILED\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
