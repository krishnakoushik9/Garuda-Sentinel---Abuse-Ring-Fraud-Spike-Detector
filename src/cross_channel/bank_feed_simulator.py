import sqlite3
import random
import logging
from typing import List, Dict
from src.config import SQLITE_DB_PATH

logger = logging.getLogger("bank_feed_simulator")

class BankFeedSimulator:
    """
    Simulates receipt of inter-bank intelligence sharing and NPCI central registries.
    In production, this runs over NPCI's secured VPA and account caution list endpoints.
    """
    OTHER_BANKS = ["SBI", "HDFC", "ICICI", "AXIS", "PNB", "CANARA"]

    def __init__(self, db_path=None):
        self.db_path = db_path or SQLITE_DB_PATH

    def simulate_inter_bank_alert(self) -> dict:
        """
        SBI or another member bank flags Account X as suspicious ->
        BOI checks if Account X matches an active BOI account.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        account_id = "ACC_UNKNOWN"
        name = "Unknown Suspect"
        risk_profile = "HIGH"
        
        try:
            cursor.execute("SELECT account_id, name, risk_profile FROM accounts ORDER BY RANDOM() LIMIT 1")
            row = cursor.fetchone()
            if row:
                account_id = row[0]
                name = row[1]
                risk_profile = row[2] or "HIGH"
        except Exception as e:
            logger.error(f"Failed to fetch random account for inter-bank alert: {e}")
        finally:
            conn.close()

        flagging_bank = random.choice(self.OTHER_BANKS)
        reasons = [
            "Mule account layering reported by merchant",
            "Rapid multi-bank layering cash-out detected",
            "Mule ring membership identified via Graph SAGE",
            "UPI VPA linked to multiple cyber-crime complaints"
        ]
        
        alert = {
            "originating_bank": flagging_bank,
            "flagged_account_id": account_id,
            "suspect_name": name,
            "risk_profile": risk_profile,
            "reason": random.choice(reasons),
            "threat_level": "HIGH",
            "action_recommended": "SUSPEND_AND_INVESTIGATE"
        }
        
        logger.info(f"Inter-bank alert received: Bank {flagging_bank} flags {account_id} -> Matching BOI account!")
        return alert

    def simulate_npci_fraud_sharing(self) -> List[dict]:
        """
        NPCI shares a central list of blocked/blacklisted UPI Virtual Payment Addresses (VPAs).
        This method simulates receiving the list and matching it against our active customer base.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        npci_list = []
        try:
            cursor.execute("SELECT account_id, name, city FROM accounts ORDER BY RANDOM() LIMIT 5")
            rows = cursor.fetchall()
            
            reasons = ["UPI_VISHING", "PHISHING_SCATTER", "MULE_FORWARDING", "CYBER_COMPLAINT"]
            for r in rows:
                vpa = f"{r[0].lower()}@ybl"
                npci_list.append({
                    "vpa": vpa,
                    "account_id": r[0],
                    "name": r[1],
                    "city": r[2],
                    "reason_code": random.choice(reasons),
                    "status": "BLOCKED",
                    "authority": "NPCI_UPILIST"
                })
        except Exception as e:
            logger.error(f"Failed to compile simulated NPCI list: {e}")
        finally:
            conn.close()
            
        return npci_list
