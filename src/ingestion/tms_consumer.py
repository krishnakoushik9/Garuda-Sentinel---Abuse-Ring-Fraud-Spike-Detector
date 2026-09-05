import logging
import sqlite3
from datetime import datetime
from src.config import SQLITE_DB_PATH
from src.ingestion.schemas import TransactionAlert
from src.ingestion.kafka_client import KafkaPubSub

logger = logging.getLogger("tms_consumer")

class TMSConsumer:
    def __init__(self, pubsub_client=None):
        self.pubsub = pubsub_client or KafkaPubSub()
        # Register local callback for reactive pub-sub simulation
        self.pubsub.subscribe("alerts.tms", self.process_message)
        logger.info("TMS Consumer initialized and registered.")

    def process_message(self, msg: dict):
        logger.info(f"TMS Consumer processing TMS alert: {msg.get('tms_alert_id')}")
        try:
            tms_alert_id = msg.get("tms_alert_id")
            rule = msg.get("rule_triggered", "")
            account_id = msg.get("account_id")
            risk_score = msg.get("risk_score", 0.0)
            txn_ids = msg.get("transaction_ids", [])
            
            # 1. Parse rule_triggered for pattern type
            if "STRUCTURING" in rule.upper():
                pattern_type = "STRUCTURING"
            elif "VELOCITY" in rule.upper():
                pattern_type = "VELOCITY_BREACH"
            elif "MULE" in rule.upper():
                pattern_type = "MULE_SUSPECTED"
            else:
                pattern_type = "TMS_RULE_BREACH"

            # 2. Cross-reference transactions in SQLite
            total_amount = 0.0
            related_accounts = set()
            channels = set()
            
            try:
                if txn_ids:
                    conn = sqlite3.connect(SQLITE_DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    placeholders = ",".join("?" for _ in txn_ids)
                    query = f"SELECT amount, sender_account, receiver_account, channel FROM transactions WHERE transaction_id IN ({placeholders})"
                    rows = cursor.execute(query, txn_ids).fetchall()
                    
                    for row in rows:
                        total_amount += row["amount"] or 0.0
                        if row["sender_account"] != account_id:
                            related_accounts.add(row["sender_account"])
                        if row["receiver_account"] != account_id:
                            related_accounts.add(row["receiver_account"])
                        if row["channel"]:
                            channels.add(row["channel"])
                            
                    conn.close()
            except Exception as e:
                logger.warning(f"SQLite transaction cross-reference failed ({e}). Proceeding with partial data.")

            primary_channel = list(channels)[0] if channels else "TRANSFER"

            # 3. Construct TransactionAlert
            ts = msg.get("alert_timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    ts = datetime.now()
            elif not isinstance(ts, datetime):
                ts = datetime.now()

            alert = TransactionAlert(
                alert_id=tms_alert_id,
                source="TMS",
                alert_type=pattern_type,
                severity="HIGH" if risk_score > 0.7 else "MEDIUM" if risk_score > 0.3 else "LOW",
                account_id=account_id,
                related_accounts=list(related_accounts),
                amount=total_amount,
                timestamp=ts,
                raw_payload=msg,
                channel=primary_channel,
                govt_ticket_id=None,
                description=f"TMS rule {rule} breached. Risk Score: {risk_score:.4f}. Note: {msg.get('analyst_notes')}"
            )

            # Publish to alerts.enriched
            alert_dict = alert.dict()
            alert_dict["timestamp"] = alert_dict["timestamp"].isoformat()
            self.pubsub.publish("alerts.enriched", alert_dict)

            # 4. Optionally trigger investigation if risk score is high
            if risk_score > 0.6:
                trigger_payload = {
                    "account_id": account_id,
                    "reason": f"TMS High Risk Trigger ({rule})",
                    "tms_alert_id": tms_alert_id,
                    "risk_score": risk_score
                }
                self.pubsub.publish("investigations.trigger", trigger_payload)
                logger.info(f"Triggered investigation for account {account_id} due to high TMS risk score: {risk_score}")
                
        except Exception as e:
            logger.error(f"TMS Consumer error: {e}")
