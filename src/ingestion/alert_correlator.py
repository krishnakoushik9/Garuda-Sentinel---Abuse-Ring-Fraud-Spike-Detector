import time
import logging
from src.ingestion.kafka_client import KafkaPubSub

logger = logging.getLogger("alert_correlator")

class AlertCorrelator:
    """
    Correlates alerts from multiple different source layers:
    - If the same account has a TMS breach AND a Govt cyber fraud ticket: Escalates to CRITICAL (risk: 1.0)
    - If the same account has an FMS alert AND a Cross-Channel Event: Escalates to HIGH (risk: 0.85)
    - Automatically queues escalated accounts on the investigations.trigger topic.
    """
    def __init__(self, pubsub_client=None, correlation_window_seconds=86400):
        self.pubsub = pubsub_client or KafkaPubSub()
        self.window = correlation_window_seconds
        
        # In-memory failsafe cache tracking historical alerts:
        # account_id -> { "source_portal": timestamp, "TMS": timestamp, "FMS": timestamp, "CROSS_CHANNEL": timestamp }
        self.account_history = {}

        # Subscribe to enriched alerts and cross-channel events
        self.pubsub.subscribe("alerts.enriched", self.process_enriched_alert)
        self.pubsub.subscribe("alerts.cross_channel", self.process_cross_channel_event)
        logger.info("Alert Correlator initialized and registered.")

    def process_enriched_alert(self, alert: dict):
        try:
            account_id = alert.get("account_id")
            source = alert.get("source")
            alert_id = alert.get("alert_id")
            
            if not account_id or not source:
                return

            self._record_and_evaluate(account_id, source, f"Alert {alert_id}")
        except Exception as e:
            logger.error(f"Alert Correlator enriched alert processing error: {e}")

    def process_cross_channel_event(self, cce: dict):
        try:
            account_id = cce.get("primary_account")
            event_id = cce.get("event_id")
            
            if not account_id:
                return

            self._record_and_evaluate(account_id, "CROSS_CHANNEL", f"CrossChannelEvent {event_id}")
        except Exception as e:
            logger.error(f"Alert Correlator cross channel processing error: {e}")

    def _record_and_evaluate(self, account_id: str, source: str, ref_id: str):
        now = time.time()
        
        if account_id not in self.account_history:
            self.account_history[account_id] = []
            
        # Add new event
        self.account_history[account_id].append({
            "source": source,
            "ref_id": ref_id,
            "timestamp": now
        })
        
        # Evict old alerts past the window
        cutoff = now - self.window
        self.account_history[account_id] = [
            ev for ev in self.account_history[account_id] if ev["timestamp"] >= cutoff
        ]
        
        # Get set of active sources
        active_sources = set(ev["source"] for ev in self.account_history[account_id])
        
        logger.info(f"Correlating account {account_id}. Active source layers in window: {list(active_sources)}")

        # 1. Escalate TMS + GOVT_CYBER -> CRITICAL
        if "TMS" in active_sources and "GOVT_CYBER" in active_sources:
            logger.warning(f"!!! CRITICAL CORRELATION !!! Account {account_id} linked to BOTH TMS Rule and Government Cyber Complaint!")
            trigger_payload = {
                "account_id": account_id,
                "reason": "CRITICAL CORRELATION: TMS Alert + Government NCRP Ticket matched in 24h window",
                "risk_score": 1.0,
                "escalated": True,
                "severity": "CRITICAL"
            }
            self.pubsub.publish("investigations.trigger", trigger_payload)
            return

        # 2. Escalate FMS + CROSS_CHANNEL -> HIGH
        if "FMS" in active_sources and "CROSS_CHANNEL" in active_sources:
            logger.warning(f"!!! HIGH RISK CORRELATION !!! Account {account_id} linked to BOTH FMS Alert and Cross-Channel Layering!")
            trigger_payload = {
                "account_id": account_id,
                "reason": "HIGH CORRELATION: FMS Alert + Cross-Channel Hopping matched in 24h window",
                "risk_score": 0.85,
                "escalated": True,
                "severity": "HIGH"
            }
            self.pubsub.publish("investigations.trigger", trigger_payload)
            return
