import argparse
import random
import sqlite3
import time
import sys
import logging
from datetime import datetime, timezone
from typing import List

from src.config import SQLITE_DB_PATH
from src.ingestion.schemas import NationalCyberAlert
from src.ingestion.kafka_client import KafkaPubSub

logger = logging.getLogger("regulatory_feed_simulator")
logging.basicConfig(level=logging.INFO)

class RegulatoryFeedSimulator:
    """
    Simulates real regulatory data feeds from RBI (CRILC), NPCI, and I4C portals.
    Queries actual accounts from the SQLite database to maintain environment consistency.
    """
    def __init__(self, pubsub_client=None):
        self.pubsub = pubsub_client or KafkaPubSub()
        self.accounts = []
        self.load_real_accounts()

    def load_real_accounts(self):
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            rows = conn.execute("SELECT account_id FROM accounts LIMIT 2000").fetchall()
            self.accounts = [r[0] for r in rows]
            conn.close()
            logger.info(f"Loaded {len(self.accounts)} real account IDs from SQLite for Regulatory Simulation.")
        except Exception as e:
            logger.error(f"Failed to load accounts from SQLite: {e}")
            self.accounts = [f"ACC{i:06d}" for i in range(1, 100)]

    def simulate_crilc_daily_update(self) -> List[dict]:
        """
        Selects ~10 accounts that show mule-like behavior and formats them
        as CRILC-reported fraudulent entities (XML-like format / structured fields).
        """
        selected_accounts = random.sample(self.accounts, min(len(self.accounts), 10))
        reports = []
        for acc in selected_accounts:
            reports.append({
                "reporting_bank": "BOI",
                "bank_code": "BOI0001",
                "account_id": acc,
                "fraud_type": random.choice(["MULE_ACCOUNT", "DORMANCY_BREAK_OUTFLOW", "RAPID_RELAY"]),
                "amount_flagged": round(random.uniform(100000.0, 5000000.0), 2),
                "reporting_date": datetime.now().date().isoformat()
            })
        return reports

    def simulate_i4c_realtime_ticket(self) -> dict:
        """
        Creates a realistic National Cyber Crime Reporting Portal (I4C) ticket.
        """
        accused = random.sample(self.accounts, min(len(self.accounts), 2))
        ticket_id = f"NCRP/2026/{random.randint(1000000, 9999999)}"
        amount = round(random.uniform(5000.0, 150000.0), 2)
        
        return {
            "ticket_id": ticket_id,
            "category": "UPI_FRAUD",
            "sub_category": random.choice(["VISHING_MULE_TRANSFER", "PART_TIME_JOB_FRAUD", "TASK_FRAUD"]),
            "accused_accounts": accused,
            "amount": amount,
            "reported_by": "CITIZEN",
            "bank_code": "BOI",
            "complainant_account": f"ACC{random.randint(50000, 99999):06d}",
            "reported_at": datetime.now().isoformat(),
            "status": "OPEN",
            "source_portal": "I4C"
        }

    def simulate_npci_vpa_block(self) -> dict:
        """Simulates blocked UPI Virtual Payment Addresses."""
        acc = random.choice(self.accounts) if self.accounts else "ACC000001"
        vpa = f"{acc.lower()}@ybl"
        return {
            "vpa": vpa,
            "account_id": acc,
            "reason_code": random.choice(["NPCI_MULE_SUSPECTED", "VELOCITY_UPI_BREACH"]),
            "effective_datetime": datetime.now().isoformat(),
            "status": "BLOCKED"
        }

    def run_feed(self, tps: float = 0.2):
        """Continuously publishes simulated regulatory updates to Kafka/Memory pub-sub."""
        logger.info(f"Starting Regulatory Ingestion Feed Simulator at rate {tps} TPS...")
        try:
            while True:
                rand = random.random()
                if rand < 0.3:
                    # 30% I4C tickets published directly to alerts.govt_cyber
                    ticket = self.simulate_i4c_realtime_ticket()
                    # Transcribe I4C accused accounts list to NationalCyberAlert compliant structure
                    alert_payload = {
                        "ticket_id": ticket["ticket_id"],
                        "complainant_account": ticket["complainant_account"],
                        "fraudulent_accounts": ticket["accused_accounts"],
                        "fraud_type": ticket["category"],
                        "amount_lost": ticket["amount"],
                        "reported_at": ticket["reported_at"],
                        "status": "OPEN",
                        "source_portal": "I4C"
                    }
                    self.pubsub.publish("alerts.govt_cyber", alert_payload)
                elif rand < 0.6:
                    # 30% NPCI blocks published to alerts.npci
                    block = self.simulate_npci_vpa_block()
                    self.pubsub.publish("alerts.npci", block)
                else:
                    # 40% CRILC reports
                    reports = self.simulate_crilc_daily_update()
                    for r in reports:
                        self.pubsub.publish("alerts.crilc", r)
                        
                time.sleep(1.0 / tps)
        except KeyboardInterrupt:
            logger.info("Regulatory Ingestion Feed halted by user.")

def test_feed():
    print("==================================================")
    print("    PS2 REGULATORY FEED SIMULATOR VERIFICATION")
    print("==================================================")
    
    pubsub = KafkaPubSub()
    sim = RegulatoryFeedSimulator(pubsub)
    
    print("\n--- 1. Testing CRILC Reports Generation ---")
    crilc_reports = sim.simulate_crilc_daily_update()
    print(f"Generated {len(crilc_reports)} CRILC reports. Sample:\n  {crilc_reports[0]}")
    
    print("\n--- 2. Testing I4C Realtime Ticket Generation ---")
    i4c_ticket = sim.simulate_i4c_realtime_ticket()
    print(f"Generated NCRP/I4C Ticket:\n  {i4c_ticket}")
    
    print("\n--- 3. Testing NPCI UPI Block Generation ---")
    npci_block = sim.simulate_npci_vpa_block()
    print(f"Generated NPCI VPA Block:\n  {npci_block}")
    
    print("\n==================================================")
    print("\033[92mREGULATORY SIMULATOR TEST PASSED\033[0m")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regulatory Feed Simulator")
    parser.add_argument("--test", action="store_true", help="Run local generator tests and exit")
    parser.add_argument("--tps", type=float, default=0.2, help="Simulator transaction rate")
    args = parser.parse_args()

    if args.test:
        test_feed()
    else:
        sim = RegulatoryFeedSimulator()
        sim.run_feed(args.tps)
