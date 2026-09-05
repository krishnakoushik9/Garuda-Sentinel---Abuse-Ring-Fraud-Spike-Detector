#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import sqlite3
import sys

API_BASE = "http://localhost:8000"
DB_PATH = "./database/ecosystem.db"

def print_result(name, success, info=""):
    color = "\033[92m[PASS]\033[0m" if success else "\033[91m[FAIL]\033[0m"
    print(f"{color} {name:<50} {info}")

def run_test(path, method="GET", data=None, headers=None):
    url = f"{API_BASE}{path}"
    req_data = None
    if data:
        if method == "POST":
            # For our investigation POST endpoint, query params are used, but if JSON is needed:
            req_data = json.dumps(data).encode('utf-8')
        else:
            url += "?" + urllib.parse.urlencode(data)
            
    req = urllib.request.Request(url, data=req_data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    elif req_data:
        req.add_header("Content-Type", "application/json")
        
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode('utf-8')
            return response.status, json.loads(body) if body else {}
    except Exception as e:
        return 500, {"error": str(e)}

def main():
    print("==================================================")
    print("      PS2 FRAUD INTELLIGENCE SYSTEM SMOKE TEST")
    print("==================================================")
    
    # 1. Read real data from SQLite for dynamic endpoint testing
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        txn_id = cursor.execute("SELECT transaction_id FROM transactions LIMIT 1").fetchone()[0]
        account_id = cursor.execute("SELECT account_id FROM accounts LIMIT 1").fetchone()[0]
        
        comm_row = cursor.execute("SELECT community_id FROM graph_analytics LIMIT 1").fetchone()
        community_id = comm_row[0] if comm_row else "0"
        
        conn.close()
        print(f"✓ Found target test parameters: txn_id={txn_id}, account_id={account_id}, community_id={community_id}")
    except Exception as e:
        print(f"\033[91mError reading SQLite db: {e}\033[0m")
        sys.exit(1)

    # List of endpoints to verify
    tests = [
        ("Health Check", "/", "GET", None),
        ("Dashboard Summary", "/api/v1/dashboard/summary", "GET", None),
        ("Transactions List", "/api/v1/transactions", "GET", {"limit": 5}),
        ("Accounts List", "/api/v1/accounts", "GET", {"limit": 5}),
        ("Graph Stats", "/api/v1/graph/stats", "GET", None),
        ("Fraud Rings", "/api/v1/graph/fraud-rings", "GET", None),
        ("Alerts List", "/api/v1/alerts", "GET", None),
        ("Single Transaction Details", f"/api/v1/transactions/{txn_id}", "GET", None),
        ("Single Account Profile", f"/api/v1/accounts/{account_id}", "GET", None),
        ("Account Network Graph", f"/api/v1/accounts/{account_id}/graph", "GET", None),
        ("Community Members", f"/api/v1/graph/community/{community_id}", "GET", None),
        ("Cognee Health Diagnostics", "/internal/cognee/health", "GET", None),
    ]

    all_passed = True

    for name, path, method, params in tests:
        status, resp = run_test(path, method, params)
        success = status in [200, 201]
        if not success:
            all_passed = False
            info = f"Status: {status}, Error: {resp.get('error', resp.get('detail', 'Unknown error'))}"
        else:
            info = "OK"
        print_result(name, success, info)

    # 12. Test Multi-Agent Investigation Route
    print("\nTesting Multi-Agent Investigation Pipeline...")
    inv_path = f"/api/v1/investigate?txn_id={txn_id}&account_id={account_id}"
    status, resp = run_test(inv_path, "POST")
    if status == 200 and "investigation_id" in resp:
        inv_id = resp["investigation_id"]
        print_result("Start Investigation (POST)", True, f"Created inv_id={inv_id}")
        
        # Test fetching the investigation status
        status2, resp2 = run_test(f"/api/v1/investigate/{inv_id}", "GET")
        if status2 == 200:
            print_result("Get Investigation Status (GET)", True, f"Status: {resp2.get('status')}")
        else:
            all_passed = False
            print_result("Get Investigation Status (GET)", False, f"Status: {status2}")
    else:
        all_passed = False
        print_result("Start Investigation (POST)", False, f"Status: {status}")

    # 13. Test Flagging Account Route
    print("\nTesting Account Flagging Endpoint...")
    flag_path = f"/api/v1/accounts/{account_id}/flag"
    status, resp = run_test(flag_path, "POST")
    if status == 200:
        print_result("Flag Account (POST)", True, resp.get("message", "Flagged successfully"))
    else:
        all_passed = False
        print_result("Flag Account (POST)", False, f"Status: {status}")

    print("\n==================================================")
    if all_passed:
        print("\033[92mALL SYSTEMS DEPLOYED AND FUNCTIONAL // SMOKE TEST PASSED\033[0m")
        sys.exit(0)
    else:
        print("\033[91mSOME ENDPOINTS RETURNED ERRORS // SMOKE TEST FAILED\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
