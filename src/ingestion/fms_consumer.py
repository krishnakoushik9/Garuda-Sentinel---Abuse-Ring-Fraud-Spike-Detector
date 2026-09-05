import logging
import sqlite3
from datetime import datetime
from src.config import SQLITE_DB_PATH
from src.ingestion.schemas import TransactionAlert
from src.ingestion.kafka_client import KafkaPubSub

logger = logging.getLogger("fms_consumer")

class FMSConsumer:
    def __init__(self, pubsub_client=None):
        self.pubsub = pubsub_client or KafkaPubSub()
        # Register local callback for reactive pub-sub simulation
        self.pubsub.subscribe("alerts.fms", self.process_message)
        logger.info("FMS Consumer initialized and registered.")

    def process_message(self, msg: dict):
        logger.info(f"FMS Consumer processing: {msg.get('alert_id')}")
        try:
            account_id = msg.get("account_id")
            
            # Enrich from SQLite/Neo4j graph layers
            pagerank = 0.0
            community_id = "N/A"
            risk_score = 0.0
            
            try:
                conn = sqlite3.connect(SQLITE_DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                row = cursor.execute(
                    "SELECT pagerank, community_id, propagated_risk_score FROM graph_analytics WHERE account_id = ?",
                    (account_id,)
                ).fetchone()
                if row:
                    pagerank = row["pagerank"] or 0.0
                    community_id = row["community_id"] or "N/A"
                    risk_score = row["propagated_risk_score"] or 0.0
                conn.close()
            except Exception as e:
                logger.warning(f"SQLite graph enrichment failed ({e}). Proceeding with default graph stats.")

            raw_payload = msg.get("raw_payload", {})
            raw_payload.update({
                "neo4j_pagerank": pagerank,
                "neo4j_community_id": community_id,
                "neo4j_risk_score": risk_score
            })
            
            # Handle timestamp
            ts = msg.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    ts = datetime.now()
            elif not isinstance(ts, datetime):
                ts = datetime.now()

            alert = TransactionAlert(
                alert_id=msg.get("alert_id"),
                source="FMS",
                alert_type=msg.get("alert_type", "MULE_SUSPECTED"),
                severity=msg.get("severity", "MEDIUM"),
                account_id=account_id,
                related_accounts=msg.get("related_accounts", []),
                amount=msg.get("amount"),
                timestamp=ts,
                raw_payload=raw_payload,
                channel=msg.get("channel"),
                govt_ticket_id=msg.get("govt_ticket_id"),
                description=msg.get("description", "Fraud Monitoring Solution triggered alert.")
            )
            
            # Convert datetime to ISO string for publishing payload
            alert_dict = alert.dict()
            alert_dict["timestamp"] = alert_dict["timestamp"].isoformat()
            
            self.pubsub.publish("alerts.enriched", alert_dict)
            logger.info(f"FMS Consumer successfully enriched & published alert: {msg.get('alert_id')}")
        except Exception as e:
            logger.error(f"FMS Consumer error: {e}")
