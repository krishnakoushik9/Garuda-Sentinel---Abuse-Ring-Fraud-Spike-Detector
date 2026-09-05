#!/usr/bin/env python3
"""Read-only dashboard API for the Phase 2 banking ecosystem runner.

The terminal runner (`./guard.sh`) owns simulation lifecycle. This server only
reads SQLite metrics so the web UI can attach to an already-running simulation.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DB_PATH = ROOT / "database" / "ecosystem.db"
LAST_TXN_COUNT = 0
LAST_METRIC_TIME = time.time()
LAST_TPS = 0.0


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.executescript(schema)


def query_one(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> int:
    row = conn.execute(sql, args).fetchone()
    return int(row[0] or 0)


def start_engine() -> dict:
    return {
        "ok": True,
        "status": "attached",
        "message": "Dashboard attached to the existing ./guard.sh runner.",
    }


def stop_engine() -> dict:
    return {
        "ok": True,
        "status": "ignored",
        "message": "Dashboard is read-only and did not stop the terminal runner.",
    }


def get_metrics() -> dict:
    global LAST_TXN_COUNT, LAST_METRIC_TIME, LAST_TPS
    init_db()
    with connect() as conn:
        txns = query_one(conn, "SELECT COUNT(*) FROM transactions")
        fraud = query_one(conn, "SELECT COUNT(*) FROM fraud_events")
        mule = query_one(conn, "SELECT COUNT(DISTINCT account_id) FROM mule_accounts")
        accounts = query_one(conn, "SELECT COUNT(*) FROM accounts")
        completed = query_one(
            conn, "SELECT COUNT(*) FROM transactions WHERE status = 'COMPLETED'"
        )
        rejected = query_one(
            conn, "SELECT COUNT(*) FROM transactions WHERE status = 'REJECTED'"
        )
        rels = query_one(conn, "SELECT COUNT(*) FROM account_relationships")
        graph_nodes = query_one(conn, "SELECT COUNT(*) FROM accounts WHERE activated_at IS NOT NULL")
        graph_edges = query_one(conn, "SELECT COUNT(*) FROM transactions")
        latest_row = conn.execute(
            "SELECT timestamp FROM transactions ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        status_row = conn.execute(
            "SELECT value FROM simulation_control WHERE key = 'status'"
        ).fetchone()

    now = time.time()
    elapsed = max(now - LAST_METRIC_TIME, 0.001)
    delta = max(txns - LAST_TXN_COUNT, 0)
    if delta > 0:
        LAST_TPS = round(delta / elapsed, 2)
    LAST_TXN_COUNT = txns
    LAST_METRIC_TIME = now

    status = "external_runner" if LAST_TPS > 0 else (status_row[0] if status_row else "attached")
    return {
        "status": status,
        "pid": None,
        "total_accounts": accounts,
        "total_transactions": txns,
        "transactions_per_second": LAST_TPS,
        "last_sample_transactions": delta,
        "latest_transaction_timestamp": latest_row[0] if latest_row else None,
        "fraud_events": fraud,
        "mule_accounts": mule,
        "completed_transactions": completed,
        "rejected_transactions": rejected,
        "relationships": rels,
        "neo4j_nodes": graph_nodes,
        "neo4j_edges": graph_edges,
        "database": str(DB_PATH),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[api] {self.address_string()} {fmt % args}")

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/metrics":
            self.send_json(get_metrics())
            return
        if parsed.path == "/api/status":
            metrics = get_metrics()
            self.send_json({"running": metrics["transactions_per_second"] > 0, **metrics})
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/start":
            self.send_json(start_engine())
            return
        if parsed.path == "/api/stop":
            self.send_json(stop_engine())
            return
        self.send_json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)


def main() -> None:
    init_db()
    host = os.environ.get("BOI_API_HOST", "127.0.0.1")
    port = int(os.environ.get("BOI_API_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Dashboard: http://{host}:{port}")
    print(f"Database:  {DB_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
