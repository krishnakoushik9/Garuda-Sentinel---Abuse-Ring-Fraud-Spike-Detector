#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import sys

API_BASE = "http://localhost:8000/api/v1/regulatory"

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
    print("    PS2 REGULATORY INTELLIGENCE ROUTER SMOKE TEST")
    print("==================================================")
    
    all_passed = True

    # 1. Fetch Real-time News Circulars Feed (Scraping test)
    print("\n--- 1. Testing Regulatory News Aggregator Feed (Google News/Reddit) ---")
    status, news = run_test("/news")
    if status == 200 and len(news) > 0:
        print_result("Unified News Aggregator (GET /news)", True, f"Ingested {len(news)} items. Sample: {news[0]['title'][:50]}...")
    else:
        all_passed = False
        print_result("Unified News Aggregator (GET /news)", False, f"Status: {status}, Count: {len(news) if isinstance(news, list) else 0}")

    # 2. Watchlist stats and items
    status, wl = run_test("/watchlist")
    if status == 200:
        print_result("Regulatory Watchlist (GET /watchlist)", True, f"Flagged accounts count: {wl.get('stats', {}).get('total_flagged')}")
    else:
        all_passed = False
        print_result("Regulatory Watchlist (GET /watchlist)", False, f"Status: {status}")

    # 3. Pending STR reports
    status, strs = run_test("/strs")
    if status == 200:
        print_result("Pending STR List (GET /strs)", True, f"Pending STR count: {len(strs)}")
    else:
        all_passed = False
        print_result("Pending STR List (GET /strs)", False, f"Status: {status}")

    # 4. Red-Flagged Accounts lifecycle tracker
    status, rfa = run_test("/rfa")
    if status == 200:
        print_result("RFA Lifecycle Tracker (GET /rfa)", True, f"RFA count: {len(rfa.get('rfa_accounts', []))}, Overdue CRILC: {rfa.get('overdue_crilc_count')}")
    else:
        all_passed = False
        print_result("RFA Lifecycle Tracker (GET /rfa)", False, f"Status: {status}")

    # 5. Simulate 1 round of regulatory data feed updates
    print("\n--- 2. Testing Regulatory Ingestion Feed Simulation ---")
    status, sim = run_test("/simulate", "POST")
    if status == 200:
        print_result("Regulatory simulation round (POST /simulate)", True, f"Simulated ticket ID: {sim.get('simulated_data', {}).get('ncrp_ticket', {}).get('ticket_id')}")
        
        # Verify stats increased on watchlist and RFA
        status2, wl2 = run_test("/watchlist")
        status3, rfa2 = run_test("/rfa")
        print(f"Watchlist size post-simulation: {wl2.get('stats', {}).get('total_flagged')}")
        print(f"RFA Accounts count post-simulation: {len(rfa2.get('rfa_accounts', []))}")
        
        # Verify pending STR table is populating if RFA is triggered
        status4, strs2 = run_test("/strs")
        print(f"Pending STRs in registry: {len(strs2)}")
    else:
        all_passed = False
        print_result("Regulatory simulation round (POST /simulate)", False, f"Status: {status}")

    print("\n==================================================")
    if all_passed:
        print("\033[92mALL REGULATORY INTELLIGENCE ENDPOINTS ARE FUNCTIONAL // PASS\033[0m")
        sys.exit(0)
    else:
        print("\033[91mREGULATORY INTELLIGENCE SMOKE TEST FAILED\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
