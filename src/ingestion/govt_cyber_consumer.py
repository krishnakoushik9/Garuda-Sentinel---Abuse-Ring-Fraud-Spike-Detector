import logging
import sqlite3
from datetime import datetime
from src.config import SQLITE_DB_PATH
from src.api.deps import get_neo4j
from src.ingestion.schemas import TransactionAlert
from src.ingestion.kafka_client import KafkaPubSub

logger = logging.getLogger("govt_cyber_consumer")

class GovtCyberConsumer:
    def __init__(self, pubsub_client=None):
        self.pubsub = pubsub_client or KafkaPubSub()
        # Register local callback for reactive pub-sub simulation
        self.pubsub.subscribe("alerts.govt_cyber", self.process_message)
        logger.info("Govt Cyber Consumer initialized and registered.")

    def process_message(self, msg: dict):
        logger.info(f"Govt Cyber Consumer processing NCRP ticket: {msg.get('ticket_id')}")
        try:
            ticket_id = msg.get("ticket_id")
            fraud_accounts = msg.get("fraudulent_accounts", [])
            source_portal = msg.get("source_portal", "NCRP")
            amount_lost = msg.get("amount_lost", 0.0)
            complainant = msg.get("complainant_account")

            # 1. Normalize and publish to alerts.enriched
            ts = msg.get("reported_at")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    ts = datetime.now()
            elif not isinstance(ts, datetime):
                ts = datetime.now()

            # We can create one enriched alert event per ticket
            alert = TransactionAlert(
                alert_id=ticket_id.replace('/', '_'),
                source="GOVT_CYBER",
                alert_type="CYBER_FRAUD_TICKET",
                severity="CRITICAL",
                account_id=fraud_accounts[0] if fraud_accounts else "UNKNOWN",
                related_accounts=fraud_accounts[1:] if len(fraud_accounts) > 1 else [],
                amount=amount_lost,
                timestamp=ts,
                raw_payload=msg,
                channel="UPI",
                govt_ticket_id=ticket_id,
                description=f"Cyber fraud complaint logged via {source_portal}. Ticket: {ticket_id}."
            )
            
            alert_dict = alert.dict()
            alert_dict["timestamp"] = alert_dict["timestamp"].isoformat()
            self.pubsub.publish("alerts.enriched", alert_dict)

            # 2. For each fraudulent account, find connected accounts (1-2 hop)
            for target_acc in fraud_accounts:
                logger.info(f"Flagging primary fraudulent account: {target_acc}")
                
                # Flag target account in SQLite
                self._flag_account_in_db(target_acc, is_primary=True)
                
                # Find neighbors (1-2 hops)
                neighbors = self._find_neighborhood(target_acc)
                logger.info(f"NCRP Ticket: Account {target_acc} connected neighborhood size: {len(neighbors)}")
                
                # Flag neighbors and queue for investigation
                for neighbor_id in neighbors:
                    self._flag_account_in_db(neighbor_id, is_primary=False)
                    
                    # Publish to investigations.trigger
                    trigger_payload = {
                        "account_id": neighbor_id,
                        "reason": f"NCRP Neighborhood Ingestion (Associated with {target_acc})",
                        "govt_ticket_id": ticket_id,
                        "risk_score": 0.9  # Automatically escalate risk score
                    }
                    self.pubsub.publish("investigations.trigger", trigger_payload)
                    
        except Exception as e:
            logger.error(f"Govt Cyber Consumer error: {e}")

    def _flag_account_in_db(self, account_id: str, is_primary: bool = False):
        try:
            # 1. Update SQLite
            conn = sqlite3.connect(SQLITE_DB_PATH)
            status_val = "GOVT_FLAGGED" if is_primary else "GOVT_ASSOCIATE"
            conn.execute("UPDATE accounts SET status = ? WHERE account_id = ?", (status_val, account_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"SQLite status update failed for {account_id} ({e})")

        # 2. Update Neo4j if available
        try:
            driver = next(get_neo4j())
            if driver:
                with driver.session() as session:
                    session.run(
                        "MATCH (a:Account {id: $aid}) SET a.status = $status, a.govt_flagged = true",
                        aid=account_id,
                        status="GOVT_FLAGGED"
                    )
        except Exception:
            pass

    def _find_neighborhood(self, account_id: str):
        neighbors = set()
        
        # Try Neo4j first
        try:
            driver = next(get_neo4j())
            if driver:
                query = """
                MATCH (a:Account {id: $account_id})-[r:SENT_TO*1..2]-(neighbor:Account)
                RETURN neighbor.id as id
                LIMIT 100
                """
                with driver.session() as session:
                    res = session.run(query, account_id=account_id)
                    for rec in res:
                        nid = rec.get("id")
                        if nid and nid != account_id:
                            neighbors.add(nid)
                if neighbors:
                    return list(neighbors)
        except Exception:
            pass
            
        # SQLite Failsafe neighborhood lookup (1-2 hops via transactions)
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()
            
            # Hop 1
            hop1 = set()
            rows1 = cursor.execute(
                "SELECT sender_account, receiver_account FROM transactions WHERE sender_account = ? OR receiver_account = ?",
                (account_id, account_id)
            ).fetchall()
            for r in rows1:
                if r[0] != account_id: hop1.add(r[0])
                if r[1] != account_id: hop1.add(r[1])
                
            # Hop 2
            hop2 = set()
            if hop1:
                placeholders = ",".join("?" for _ in hop1)
                query2 = f"SELECT sender_account, receiver_account FROM transactions WHERE sender_account IN ({placeholders}) OR receiver_account IN ({placeholders})"
                rows2 = cursor.execute(query2, list(hop1) + list(hop1)).fetchall()
                for r in rows2:
                    if r[0] != account_id and r[0] not in hop1: hop2.add(r[0])
                    if r[1] != account_id and r[1] not in hop1: hop2.add(r[1])
                    
            conn.close()
            return list(hop1.union(hop2))
        except Exception as e:
            logger.error(f"Failsafe SQLite neighborhood query failed ({e})")
            return []
