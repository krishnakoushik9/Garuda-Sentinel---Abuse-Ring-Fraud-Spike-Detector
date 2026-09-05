#!/usr/bin/env python3
"""Switch the active data source between COBOL synthetic and real bank data.

Usage:
    python scripts/switch_datasource.py --source cobol
    python scripts/switch_datasource.py --source real
    python scripts/switch_datasource.py --status
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "database" / "ecosystem.db"


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def show_status(db_path: str) -> None:
    conn = get_conn(db_path)
    row = conn.execute(
        "SELECT value FROM simulation_control WHERE key = 'data_source'"
    ).fetchone()
    active = row["value"] if row else "COBOL_SYNTHETIC"

    cobol_count = conn.execute(
        "SELECT COUNT(*) FROM accounts WHERE account_id LIKE 'ACC%'"
    ).fetchone()[0]

    # Check if dataset_accounts exists
    real_count = 0
    real_mules = 0
    try:
        real_count = conn.execute("SELECT COUNT(*) FROM dataset_accounts").fetchone()[0]
        real_mules = conn.execute(
            "SELECT COUNT(*) FROM dataset_accounts WHERE is_mule = 1"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        pass  # table doesn't exist yet

    conn.close()

    print("┌─────────────────────────────────────────┐")
    print("│  Data Source Status                     │")
    print("├────────────────────┬────────────────────┤")
    print(f"│  Active source     │ {active:>18} │")
    print(f"│  COBOL accounts    │ {cobol_count:>18,} │")
    print(f"│  Real accounts     │ {real_count:>18,} │")
    print(f"│  Real mules        │ {real_mules:>18,} │")
    print("└────────────────────┴────────────────────┘")


def switch_to_real(db_path: str) -> None:
    conn = get_conn(db_path)

    # Check dataset_accounts has rows
    try:
        count = conn.execute("SELECT COUNT(*) FROM dataset_accounts").fetchone()[0]
    except sqlite3.OperationalError:
        count = 0

    if count == 0:
        print("✗ No real bank data found. Run ingest_dataset.py first.")
        conn.close()
        sys.exit(1)

    now = datetime.now().isoformat(timespec="seconds")

    # Update data_source_registry
    try:
        conn.execute("UPDATE data_source_registry SET is_active = 0")
        conn.execute(
            "UPDATE data_source_registry SET is_active = 1 "
            "WHERE source_type = 'REGULATORY_FEED'"
        )
    except sqlite3.OperationalError:
        pass

    # Update simulation_control
    for key, val in [
        ("data_source", "REGULATORY_FEED"),
        ("status", "finished"),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO simulation_control (key, value, updated_at) VALUES (?,?,?)",
            (key, val, now),
        )

    conn.commit()
    conn.close()
    print(f"✓ Switched to REGULATORY_FEED ({count:,} accounts active)")


def switch_to_cobol(db_path: str) -> None:
    conn = get_conn(db_path)

    count = conn.execute(
        "SELECT COUNT(*) FROM accounts WHERE account_id LIKE 'ACC%'"
    ).fetchone()[0]

    if count == 0:
        print("✗ No COBOL synthetic data found. Run COBOL engine first.")
        conn.close()
        sys.exit(1)

    now = datetime.now().isoformat(timespec="seconds")

    # Update data_source_registry
    try:
        conn.execute("UPDATE data_source_registry SET is_active = 0")
        conn.execute(
            "UPDATE data_source_registry SET is_active = 1 "
            "WHERE source_type = 'COBOL_SYNTHETIC'"
        )
    except sqlite3.OperationalError:
        pass

    for key, val in [
        ("data_source", "COBOL_SYNTHETIC"),
        ("status", "finished"),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO simulation_control (key, value, updated_at) VALUES (?,?,?)",
            (key, val, now),
        )

    conn.commit()
    conn.close()
    print(f"✓ Switched to COBOL_SYNTHETIC ({count:,} accounts active)")


def main():
    parser = argparse.ArgumentParser(description="Switch active data source")
    parser.add_argument("--source", choices=["cobol", "real"], help="Source to activate")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite DB")
    args = parser.parse_args()

    if args.status:
        show_status(args.db)
    elif args.source == "real":
        switch_to_real(args.db)
    elif args.source == "cobol":
        switch_to_cobol(args.db)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
