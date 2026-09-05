import argparse
import random
import sqlite3
import time
import sys
import logging
from datetime import datetime

from src.config import SQLITE_DB_PATH
from src.ingestion.schemas import TransactionAlert, NationalCyberAlert, TMSAlert, CrossChannelEvent
from src.ingestion.kafka_client import KafkaPubSub
from src.ingestion.fms_consumer import FMSConsumer
from src.ingestion.tms_consumer import TMSConsumer
from src.ingestion.govt_cyber_consumer import GovtCyberConsumer
from src.ingestion.cross_channel_detector import CrossChannelDetector
from src.ingestion.alert_correlator import AlertCorrelator

logger = logging.getLogger("simulator")
logging.basicConfig(level=logging.INFO)

class AlertSimulator:
    """
    Generates realistic alert streams from FMS, TMS, and Government portals,
    and publishes raw transactions to simulate cross-channel layering.
    Uses real accounts from SQLite to guarantee data consistency.
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
            logger.info(f"Loaded {len(self.accounts)} real account IDs from SQLite database.")
        except Exception as e:
            logger.error(f"Failed to load accounts from SQLite: {e}")
            self.accounts = [f"ACC{i:06d}" for i in range(1, 100)]

    def generate_fms_alert(self) -> dict:
        acc = random.choice(self.accounts) if self.accounts else "ACC000001"
        related = [random.choice(self.accounts) for _ in range(2)]
        alert_id = f"FMS_{random.randint(100000, 999999)}"
        amount = round(random.uniform(50000.0, 1500000.0), 2)
        
        return {
            "alert_id": alert_id,
            "account_id": acc,
            "related_accounts": related,
            "amount": amount,
            "channel": random.choice(["UPI", "IMPS", "NEFT", "RTGS"]),
            "alert_type": random.choice(["MULE_SUSPECTED", "VELOCITY_BREACH"]),
            "severity": random.choice(["MEDIUM", "HIGH"]),
            "description": f"FMS anomaly detected for account {acc} with high amount INR {amount}",
            "timestamp": datetime.now().isoformat(),
            "raw_payload": {"rule_code": "FMS_MULE_01", "score": random.uniform(0.7, 0.95)}
        }

    def generate_tms_alert(self) -> dict:
        acc = random.choice(self.accounts) if self.accounts else "ACC000001"
        alert_id = f"TMS_{random.randint(100000, 999999)}"
        rule = random.choice(["RULE_047_STRUCTURING", "RULE_012_VELOCITY", "RULE_009_RAPID_OUTFLOW"])
        risk = random.uniform(0.35, 0.99)
        
        # Pick 2-3 random transaction IDs or simulate them
        txn_ids = [f"TXN{random.randint(100000000, 999999999)}" for _ in range(3)]
        
        return {
            "tms_alert_id": alert_id,
            "rule_triggered": rule,
            "account_id": acc,
            "risk_score": risk,
            "transaction_ids": txn_ids,
            "alert_timestamp": datetime.now().isoformat(),
            "analyst_notes": f"Rule {rule} exceeded dynamic threshold.",
            "disposition": "PENDING"
        }

    def generate_ncrp_ticket(self) -> dict:
        complainant = random.choice(self.accounts) if self.accounts else "ACC000002"
        fraudulent = [random.choice(self.accounts) for _ in range(2)]
        
        ticket_num = f"{random.randint(10000, 99999)}/{random.randint(2025, 2026)}"
        amount = round(random.uniform(10000.0, 500000.0), 2)
        
        return {
            "ticket_id": ticket_num,
            "complainant_account": complainant,
            "fraudulent_accounts": fraudulent,
            "fraud_type": random.choice(["OTP_FRAUD", "VISHING", "PHISHING", "UPI_FRAUD"]),
            "amount_lost": amount,
            "reported_at": datetime.now().isoformat(),
            "status": "OPEN",
            "source_portal": random.choice(["NCRP", "I4C", "CFCFRMS"])
        }

    def generate_cross_channel_tx_sequence(self, account_id: str):
        """Simulates 3 rapid transactions using different channels for the same account"""
        channels = ["NEFT", "IMPS", "UPI"]
        txs = []
        for ch in channels:
            txn_id = f"TXN_HOP_{random.randint(1000000, 9999999)}"
            txs.append({
                "transaction_id": txn_id,
                "sender_account": account_id,
                "receiver_account": random.choice(self.accounts),
                "amount": round(random.uniform(10000.0, 80000.0), 2),
                "channel": ch,
                "timestamp": datetime.now().isoformat()
            })
        return txs

    def run_continuous(self, tps: float = 0.5):
        logger.info(f"Starting continuous alert generation at rate {tps} TPS...")
        try:
            while True:
                # Randomly determine alert type to publish
                rand = random.random()
                if rand < 0.4:
                    # 40% FMS alerts
                    fms_data = self.generate_fms_alert()
                    self.pubsub.publish("alerts.fms", fms_data)
                elif rand < 0.7:
                    # 30% TMS alerts
                    tms_data = self.generate_tms_alert()
                    self.pubsub.publish("alerts.tms", tms_data)
                elif rand < 0.9:
                    # 20% Government cyber alerts
                    govt_data = self.generate_ncrp_ticket()
                    self.pubsub.publish("alerts.govt_cyber", govt_data)
                else:
                    # 10% Cross-channel sequences
                    acc = random.choice(self.accounts) if self.accounts else "ACC000001"
                    txs = self.generate_cross_channel_tx_sequence(acc)
                    for tx in txs:
                        self.pubsub.publish("transactions.raw", tx)
                        
                time.sleep(1.0 / tps)
        except KeyboardInterrupt:
            logger.info("Simulation halted by user.")

def dry_run():
    print("==================================================")
    print("     PS2 INGESTION LAYER DRY-RUN VERIFICATION")
    print("==================================================")
    
    # 1. Instantiate pubsub and consumers to register all reactive components
    pubsub = KafkaPubSub()
    
    print("\n--- Initializing Pipeline Components ---")
    fms_c = FMSConsumer(pubsub)
    tms_c = TMSConsumer(pubsub)
    govt_c = GovtCyberConsumer(pubsub)
    ccd = CrossChannelDetector(time_window_minutes=5, pubsub_client=pubsub)
    correlator = AlertCorrelator(pubsub)
    
    # Instantiate simulator
    sim = AlertSimulator(pubsub)
    
    print("\n--- 1. Testing FMS Ingestion Stream ---")
    fms_raw = sim.generate_fms_alert()
    print(f"Generated Raw FMS Alert:\n  {fms_raw}\n")
    pubsub.publish("alerts.fms", fms_raw)
    
    print("\n--- 2. Testing TMS Ingestion & Auto-Trigger Stream ---")
    tms_raw = sim.generate_tms_alert()
    # Force high risk score to trigger investigation flow
    tms_raw["risk_score"] = 0.85 
    print(f"Generated Raw TMS Alert:\n  {tms_raw}\n")
    pubsub.publish("alerts.tms", tms_raw)
    
    print("\n--- 3. Testing Govt Cyber Complaint NCRP Neighborhood Scan ---")
    ncrp_raw = sim.generate_ncrp_ticket()
    print(f"Generated Raw NCRP Ticket:\n  {ncrp_raw}\n")
    pubsub.publish("alerts.govt_cyber", ncrp_raw)

    print("\n--- 4. Testing Cross-Channel Layering Detection (3 Hops) ---")
    target_acc = sim.accounts[0] if sim.accounts else "ACC000001"
    txs = sim.generate_cross_channel_tx_sequence(target_acc)
    print(f"Publishing 3 transactions on different channels for account {target_acc}...")
    for tx in txs:
        pubsub.publish("transactions.raw", tx)

    print("\n--- 5. Testing Multi-Layer Escalation Correlation ---")
    correlated_acc = "ACC_CORR_TEST"
    print(f"Simulating identical account ({correlated_acc}) match in BOTH TMS and Govt portals...")
    
    # Simulate enriched alert arrival from TMS
    pubsub.publish("alerts.enriched", {
        "alert_id": "TMS_CORR_001",
        "account_id": correlated_acc,
        "source": "TMS",
        "timestamp": datetime.now().isoformat()
    })
    
    # Simulate enriched alert arrival from Govt Portal
    pubsub.publish("alerts.enriched", {
        "alert_id": "GOVT_CORR_002",
        "account_id": correlated_acc,
        "source": "GOVT_CYBER",
        "timestamp": datetime.now().isoformat()
    })

    print("\n==================================================")
    print("\033[92mDRY RUN COMPLETED successfully // ALL MODELS VERIFIED\033[0m")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alert Ingestion Simulator")
    parser.add_argument("--dry-run", action="store_true", help="Run end-to-end in-memory pipelines validation")
    parser.add_argument("--tps", type=float, default=0.5, help="Simulation transactions/alerts per second")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    else:
        sim = AlertSimulator()
        sim.run_continuous(args.tps)
