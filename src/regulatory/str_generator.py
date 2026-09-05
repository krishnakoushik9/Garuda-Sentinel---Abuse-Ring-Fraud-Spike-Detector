import json
import sqlite3
import logging
from datetime import datetime
import uuid

from src.config import SQLITE_DB_PATH
from src.ingestion.kafka_client import KafkaPubSub

logger = logging.getLogger("str_generator")


def get_fraud_context(fraud_category: str, amount: float) -> dict:
    from src.ingestion.govdata_injector import GovDataInjector

    return GovDataInjector().get_fraud_context(fraud_category=fraud_category, amount=amount)

class STRGenerator:
    """
    Generates Suspicious Transaction Reports (STRs) matching FIU-IND formats
    per PMLA Section 12 requirements. Persists to SQLite and publishes to str.pending.
    """
    def __init__(self, pubsub_client=None):
        self.pubsub = pubsub_client or KafkaPubSub()
        self.init_db()

    def init_db(self):
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS str_reports (
                    str_id TEXT PRIMARY KEY,
                    filing_date TEXT,
                    reporting_entity TEXT,
                    account_id TEXT,
                    risk_score REAL,
                    verdict TEXT,
                    amount_involved REAL,
                    narrative TEXT,
                    regulatory_basis TEXT,
                    status TEXT,
                    requires_analyst_review INTEGER,
                    raw_document TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info("SQLite str_reports table verified/created successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize str_reports table: {e}")

    def generate_str(self, investigation_result: dict) -> dict:
        str_id = f"STR/{datetime.now().year}/{uuid.uuid4().hex[:8].upper()}"
        
        # Pull details
        account_id = investigation_result.get("account_id", "UNKNOWN")
        risk_score = investigation_result.get("final_risk_score", 0.0)
        verdict = investigation_result.get("final_verdict", "SUSPICIOUS")
        
        # Aggregate amounts and patterns
        patterns = investigation_result.get("patterns_detected", [])
        if not patterns and "graph_findings" in investigation_result:
            patterns = investigation_result["graph_findings"]
            
        total_amount = investigation_result.get("total_amount", 0.0)
        if total_amount == 0.0 and "amount" in investigation_result:
            total_amount = investigation_result["amount"]

        fraud_category = "UPI_FRAUD"
        if isinstance(patterns, list) and patterns:
            first_pattern = patterns[0]
            if isinstance(first_pattern, str):
                fraud_category = first_pattern.upper().replace(" ", "_")
            elif isinstance(first_pattern, dict):
                fraud_category = str(first_pattern.get("category") or first_pattern.get("pattern") or "UPI_FRAUD").upper()

        fraud_context = {}
        fraud_context_text = ""
        try:
            fraud_context = get_fraud_context(fraud_category, float(total_amount or 0.0))
            if fraud_context.get("year"):
                fraud_context_text = (
                    f" According to RBI official fraud data (data.gov.in, resource 3d50bf0b), "
                    f"{fraud_context.get('num_cases_this_year', 0)} cases of "
                    f"{fraud_context.get('fraud_category', fraud_category)} fraud were reported in "
                    f"{fraud_context.get('year')}, with average amount "
                    f"₹{fraud_context.get('national_avg_fraud_amount_rupees', 0):,.2f}. "
                    f"This transaction at ₹{float(total_amount or 0.0):,.2f} represents the "
                    f"{fraud_context.get('percentile_rank', 0)}th percentile."
                )
        except Exception as e:
            logger.warning(f"Failed to enrich STR with RBI fraud context: {e}")

        base_narrative = investigation_result.get(
            "explanation_narrative",
            investigation_result.get("explanation", "Suspicious transactional routing pattern observed.")
        )

        str_doc = {
            "str_id": str_id,
            "filing_date": datetime.now().isoformat(),
            "reporting_entity": "BANK_OF_INDIA",
            "branch_code": "BOI_HQ",
            "account_details": {
                "account_id": account_id,
                "account_type": "SAVINGS/CURRENT",
                "risk_score": risk_score,
                "verdict": verdict,
            },
            "suspicious_activity": {
                "pattern": patterns,
                "amount_involved": total_amount,
                "time_period": "LAST_30_DAYS",
                "graph_evidence": investigation_result.get("graph_findings", {}),
            },
            "narrative": f"{base_narrative}{fraud_context_text}",
            "shap_evidence": investigation_result.get("shap_top_factors", []),
            "gov_fraud_context": fraud_context,
            "regulatory_basis": [
                "RBI Master Directions on Fraud Risk Management 2024",
                "PMLA Section 12 - STR Filing Obligation",
                "FATF Recommendation 20"
            ],
            "status": "PENDING_REVIEW",
            "auto_generated": True,
            "requires_analyst_review": True
        }
        return str_doc

    def save_str(self, str_doc: dict) -> str:
        str_id = str_doc.get("str_id")
        acc_details = str_doc.get("account_details", {})
        activity = str_doc.get("suspicious_activity", {})
        
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.execute(
                """
                INSERT INTO str_reports (
                    str_id, filing_date, reporting_entity, account_id, 
                    risk_score, verdict, amount_involved, narrative, 
                    regulatory_basis, status, requires_analyst_review, raw_document
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str_id,
                    str_doc.get("filing_date"),
                    str_doc.get("reporting_entity"),
                    acc_details.get("account_id"),
                    acc_details.get("risk_score"),
                    acc_details.get("verdict"),
                    activity.get("amount_involved"),
                    str_doc.get("narrative"),
                    json.dumps(str_doc.get("regulatory_basis")),
                    str_doc.get("status"),
                    1 if str_doc.get("requires_analyst_review") else 0,
                    json.dumps(str_doc)
                )
            )
            conn.commit()
            conn.close()
            logger.info(f"STR report {str_id} saved to database.")
        except Exception as e:
            logger.error(f"Failed to save STR {str_id} to SQLite: {e}")

        # Publish to str.pending
        try:
            self.pubsub.publish("str.pending", str_doc)
        except Exception as e:
            logger.warning(f"Failed to publish STR pending topic: {e}")
            
        return str_id

    def get_pending_strs(self) -> list:
        pending = []
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT raw_document FROM str_reports WHERE status = 'PENDING_REVIEW'").fetchall()
            for r in rows:
                pending.append(json.loads(r[0]))
            conn.close()
        except Exception as e:
            logger.error(f"Failed to fetch pending STRs from SQLite: {e}")
        return pending

    def mark_str_filed(self, str_id: str, analyst_id: str):
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            row = conn.execute("SELECT raw_document FROM str_reports WHERE str_id = ?", (str_id,)).fetchone()
            if row:
                doc = json.loads(row[0])
                doc["status"] = "FILED"
                doc["filed_by"] = analyst_id
                doc["filed_at"] = datetime.now().isoformat()
                
                conn.execute(
                    "UPDATE str_reports SET status = 'FILED', raw_document = ? WHERE str_id = ?",
                    (json.dumps(doc), str_id)
                )
                conn.commit()
                logger.info(f"STR report {str_id} marked as FILED by analyst {analyst_id}.")
            conn.close()
        except Exception as e:
            logger.error(f"Failed to mark STR {str_id} as filed: {e}")
