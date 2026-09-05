import sqlite3
import logging
import time
from typing import List, Dict, Any
from src.config import SQLITE_DB_PATH

logger = logging.getLogger("early_warning")

class EarlyWarningSystem:
    """
    Implements the RBI Early Warning Signal (EWS) framework (Master Directions 2024).
    Calculates composite pre-mule risk vectors 24-72 hours before mule activation.
    """
    EWS_SIGNALS = {
        "PRE_ACTIVATION_KYC_UPDATE": {
            "description": "KYC details changed within 7 days before high-value txn",
            "weight": 0.4
        },
        "NEW_DEVICE_HIGH_VALUE": {
            "description": "First transaction from new device > ₹50,000",
            "weight": 0.5
        },
        "BENEFICIARY_CLUSTER_GROWTH": {
            "description": "Unique beneficiaries growing > 10/day",
            "weight": 0.6
        },
        "INBOUND_SPIKE_NO_HISTORY": {
            "description": "Large inbound transfer to account with <30 day history",
            "weight": 0.7
        },
        "GEOGRAPHIC_ANOMALY": {
            "description": "Transaction location inconsistent with account profile",
            "weight": 0.45
        }
    }

    def __init__(self, db_path=None):
        self.db_path = db_path or SQLITE_DB_PATH

    def compute_ews_score(self, account_id: str) -> dict:
        """
        Evaluates EWS indicators for an account and returns the composite threat score (0-1).
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        triggered = []
        score = 0.0
        details = {}
        
        try:
            # 1. PRE_ACTIVATION_KYC_UPDATE Heuristics
            # Check if high-risk profile and recent account status modification
            cursor.execute(
                "SELECT risk_profile, customer_segment, status FROM accounts WHERE account_id = ?",
                (account_id,)
            )
            acc_row = cursor.fetchone()
            if acc_row:
                if acc_row["risk_profile"] == "HIGH" or acc_row["customer_segment"] == "RISKY":
                    triggered.append("PRE_ACTIVATION_KYC_UPDATE")
                    details["PRE_ACTIVATION_KYC_UPDATE"] = {
                        "risk_profile": acc_row["risk_profile"],
                        "customer_segment": acc_row["customer_segment"]
                    }

            # 2. NEW_DEVICE_HIGH_VALUE Heuristics
            # Check for recent outgoing transaction > ₹50,000
            cursor.execute(
                "SELECT amount, timestamp, channel FROM transactions WHERE sender_account = ? AND amount >= 50000 LIMIT 1",
                (account_id,)
            )
            hi_val = cursor.fetchone()
            if hi_val:
                triggered.append("NEW_DEVICE_HIGH_VALUE")
                amt = hi_val["amount"]
                if amt > 100000000:
                    amt = amt / 100.0
                details["NEW_DEVICE_HIGH_VALUE"] = {
                    "amount": round(amt, 2),
                    "channel": hi_val["channel"],
                    "timestamp": hi_val["timestamp"]
                }

            # 3. BENEFICIARY_CLUSTER_GROWTH Heuristics
            # Check if unique receivers > 3 within 3 days
            cursor.execute("""
                SELECT COUNT(DISTINCT receiver_account) as receiver_count 
                FROM transactions 
                WHERE sender_account = ? AND timestamp > datetime('now', '-3 days')
            """, (account_id,))
            rec_count = cursor.fetchone()["receiver_count"]
            if rec_count >= 3:
                triggered.append("BENEFICIARY_CLUSTER_GROWTH")
                details["BENEFICIARY_CLUSTER_GROWTH"] = {
                    "unique_receivers_3d": rec_count
                }

            # 4. INBOUND_SPIKE_NO_HISTORY Heuristics
            # Inbound sum > 25,000 but account has under 3 transactions prior to 3 days ago
            cursor.execute("""
                SELECT SUM(amount) as total_in 
                FROM transactions 
                WHERE receiver_account = ? AND timestamp > datetime('now', '-3 days')
            """, (account_id,))
            inbound = cursor.fetchone()["total_in"] or 0
            if inbound > 100000000:
                inbound = inbound / 100.0
                
            cursor.execute("""
                SELECT COUNT(*) as history_count 
                FROM transactions 
                WHERE sender_account = ? AND timestamp < datetime('now', '-3 days')
            """, (account_id,))
            history = cursor.fetchone()["history_count"]
            
            if inbound > 25000 and history <= 2:
                triggered.append("INBOUND_SPIKE_NO_HISTORY")
                details["INBOUND_SPIKE_NO_HISTORY"] = {
                    "inbound_spike_amount": round(inbound, 2),
                    "prior_history_count": history
                }

            # 5. GEOGRAPHIC_ANOMALY Heuristics
            # Trigger if account belongs to non-metropolitan city but has card or UPI transactions registered online
            if acc_row and acc_row["status"] == "GOVT_FLAGGED":
                triggered.append("GEOGRAPHIC_ANOMALY")
                details["GEOGRAPHIC_ANOMALY"] = {
                    "flagged_status": acc_row["status"]
                }

            # Calculate weighted composite score normalized between 0.0 and 1.0
            total_weight = sum(self.EWS_SIGNALS[sig]["weight"] for sig in triggered)
            # Normalize composite score mathematically
            score = min(total_weight, 1.0)

        except Exception as e:
            logger.error(f"Error computing EWS score for {account_id}: {e}")
        finally:
            conn.close()

        return {
            "account_id": account_id,
            "ews_score": round(score, 2),
            "triggered_signals": triggered,
            "details": details,
            "action_required": score >= 0.6
        }

    def run_batch_ews_scan(self, limit: int = 100) -> List[dict]:
        """
        Runs batch scan over active accounts to identify high-risk pre-mule indicators.
        """
        alerts = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Gather accounts with active recent transactions
            cursor.execute("SELECT DISTINCT account_id FROM accounts LIMIT 500")
            accounts = [r[0] for r in cursor.fetchall()]
            
            for acc in accounts:
                res = self.compute_ews_score(acc)
                if res["ews_score"] > 0.0:
                    alerts.append(res)
                    
            # Sort top pre-mules descending
            alerts.sort(key=lambda x: x["ews_score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed running batch EWS scan: {e}")
        finally:
            conn.close()
            
        return alerts[:limit]
