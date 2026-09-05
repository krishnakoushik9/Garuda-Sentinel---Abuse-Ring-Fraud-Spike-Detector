import sqlite3
import logging
from datetime import datetime, timedelta
import json

from src.config import SQLITE_DB_PATH
from src.api.deps import get_neo4j

logger = logging.getLogger("rfa_tracker")

class RFATracker:
    """
    Tracks RBI Red-Flagged Account (RFA) lifecycle events.
    Enforces compliance with:
    - 7-day CRILC reporting deadlines
    - 180-day fraud classification deadlines
    """
    def __init__(self):
        self.init_db()

    def init_db(self):
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rfa_accounts (
                    account_id TEXT PRIMARY KEY,
                    reason TEXT,
                    evidence TEXT,
                    flagged_date TEXT,
                    crilc_report_deadline TEXT,
                    crilc_reported INTEGER DEFAULT 0,
                    crilc_reported_date TEXT,
                    fraud_classification_deadline TEXT,
                    classification TEXT DEFAULT 'PENDING',
                    classified_date TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info("SQLite rfa_accounts table verified/created successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize rfa_accounts table: {e}")

    def flag_account(self, account_id: str, reason: str, evidence: dict):
        logger.info(f"Flagging account {account_id} as RFA (Red-Flagged Account) per RBI guidelines.")
        
        now = datetime.now()
        flagged_date = now.isoformat()
        crilc_deadline = (now + timedelta(days=7)).isoformat()
        classification_deadline = (now + timedelta(days=180)).isoformat()

        # 1. Update SQLite RFA accounts table
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.execute(
                """
                INSERT INTO rfa_accounts (
                    account_id, reason, evidence, flagged_date, 
                    crilc_report_deadline, fraud_classification_deadline
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET 
                    reason=excluded.reason, 
                    evidence=excluded.evidence,
                    flagged_date=excluded.flagged_date,
                    crilc_report_deadline=excluded.crilc_report_deadline,
                    fraud_classification_deadline=excluded.fraud_classification_deadline
                """,
                (
                    account_id,
                    reason,
                    json.dumps(evidence),
                    flagged_date,
                    crilc_deadline,
                    classification_deadline
                )
            )
            # Update main accounts table status to RFA
            conn.execute("UPDATE accounts SET status = 'RFA' WHERE account_id = ?", (account_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record RFA state for {account_id} in SQLite: {e}")

        # 2. Update Neo4j node properties
        try:
            driver = next(get_neo4j())
            if driver:
                with driver.session() as session:
                    session.run(
                        "MATCH (a:Account {id: $aid}) SET a.is_rfa = true, a.status = 'RFA'",
                        aid=account_id
                    )
        except Exception:
            pass

    def mark_crilc_reported(self, account_id: str):
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.execute(
                "UPDATE rfa_accounts SET crilc_reported = 1, crilc_reported_date = ? WHERE account_id = ?",
                (datetime.now().isoformat(), account_id)
            )
            conn.commit()
            conn.close()
            logger.info(f"RFA account {account_id} reported to CRILC.")
        except Exception as e:
            logger.error(f"Failed to update CRILC reported status: {e}")

    def classify_rfa_account(self, account_id: str, classification: str):
        """Classifies as FRAUD, SUSPICIOUS, or CLEARED within 180 days."""
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.execute(
                "UPDATE rfa_accounts SET classification = ?, classified_date = ? WHERE account_id = ?",
                (classification.upper(), datetime.now().isoformat(), account_id)
            )
            # Sync back to status in main accounts
            main_status = "MULE_CONFIRMED" if classification.upper() == "FRAUD" else "CLEARED" if classification.upper() == "CLEARED" else "SUSPICIOUS"
            conn.execute("UPDATE accounts SET status = ? WHERE account_id = ?", (main_status, account_id))
            conn.commit()
            conn.close()
            logger.info(f"RFA account {account_id} classified as {classification.upper()}.")
        except Exception as e:
            logger.error(f"Failed to classify RFA account {account_id}: {e}")

    def get_overdue_crilc_reports(self) -> list:
        """Returns accounts past the 7-day reporting deadline that have not been reported."""
        overdue = []
        now = datetime.now().isoformat()
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM rfa_accounts WHERE crilc_reported = 0 AND crilc_report_deadline < ?",
                (now,)
            ).fetchall()
            for r in rows:
                overdue.append(dict(r))
            conn.close()
        except Exception as e:
            logger.error(f"Failed to fetch overdue CRILC accounts: {e}")
        return overdue

    def get_pending_classifications(self) -> list:
        """Returns accounts needing classification before the 180-day deadline."""
        pending = []
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM rfa_accounts WHERE classification = 'PENDING'").fetchall()
            for r in rows:
                pending.append(dict(r))
            conn.close()
        except Exception as e:
            logger.error(f"Failed to fetch pending RFA classifications: {e}")
        return pending
