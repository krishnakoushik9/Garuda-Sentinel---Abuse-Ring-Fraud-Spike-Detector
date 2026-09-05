import time
import uuid
import logging
from src.ingestion.schemas import CrossChannelEvent
from src.ingestion.kafka_client import KafkaPubSub
from src.api.deps import get_redis

logger = logging.getLogger("cross_channel_detector")

class CrossChannelDetector:
    """
    Correlates multi-channel layered hopping.
    Triggers a CrossChannelEvent when an account uses >= 3 different transfer channels
    (e.g., NEFT -> IMPS -> UPI) within a sliding 60-minute window.
    """
    def __init__(self, redis_client=None, time_window_minutes=60, pubsub_client=None):
        self.redis = redis_client
        self.redis_failed = False
        self.window = time_window_minutes
        self.pubsub = pubsub_client or KafkaPubSub()
        self.fallback_store = {}  # Failsafe in-memory cache if Redis is offline

        # Register local callback for raw transaction stream
        self.pubsub.subscribe("transactions.raw", self.process_transaction)
        logger.info("Cross Channel Detector initialized and registered.")

    def process_transaction(self, txn: dict):
        try:
            account_id = txn.get("sender_account")
            channel = txn.get("channel")
            txn_id = txn.get("transaction_id")
            amount = txn.get("amount", 0.0)
            
            if not account_id or not channel or not txn_id:
                return

            now = time.time()
            channels_used = set()
            recent_txns = []

            # 1. Try Redis correlation
            redis_online = False
            if self.redis is None and not self.redis_failed:
                try:
                    self.redis = next(get_redis())
                    if self.redis is None:
                        self.redis_failed = True
                except Exception:
                    self.redis_failed = True

            if self.redis:
                try:
                    key = f"channels:{account_id}"
                    # Add current transaction to ZSET
                    self.redis.zadd(key, {f"{channel}:{txn_id}:{amount}": now})
                    self.redis.expire(key, self.window * 60)
                    
                    # Remove older than window
                    self.redis.zremrangebyscore(key, 0, now - self.window * 60)
                    
                    # Fetch active set
                    records = self.redis.zrange(key, 0, -1)
                    for r in records:
                        if isinstance(r, bytes):
                            r = r.decode('utf-8')
                        ch, tid, amt = r.split(':')
                        channels_used.add(ch)
                        recent_txns.append({"channel": ch, "txn_id": tid, "amount": float(amt)})
                    
                    redis_online = True
                except Exception as ex:
                    logger.warning(f"Redis cross-channel tracking failed ({ex}). Reverting to in-memory failsafe.")

            # 2. Resilient In-Memory Fallback
            if not redis_online:
                if account_id not in self.fallback_store:
                    self.fallback_store[account_id] = []
                
                # Append current
                self.fallback_store[account_id].append((channel, txn_id, amount, now))
                
                # Filter old records
                cutoff = now - (self.window * 60)
                self.fallback_store[account_id] = [
                    item for item in self.fallback_store[account_id] if item[3] >= cutoff
                ]
                
                for ch, tid, amt, _ in self.fallback_store[account_id]:
                    channels_used.add(ch)
                    recent_txns.append({"channel": ch, "txn_id": tid, "amount": amt})

            # 3. Detect Hop Breach
            if len(channels_used) >= 3:
                event_id = f"CCE_{str(uuid.uuid4())[:8].upper()}"
                total_amt = sum(item["amount"] for item in recent_txns)
                
                cce = CrossChannelEvent(
                    event_id=event_id,
                    primary_account=account_id,
                    channels_involved=list(channels_used),
                    total_amount=total_amt,
                    time_window_minutes=self.window,
                    transaction_count=len(recent_txns),
                    pattern="CHANNEL_HOPPING"
                )
                
                logger.info(f"Cross Channel Breach Detected on account {account_id}! Channels: {list(channels_used)}")
                self.pubsub.publish("alerts.cross_channel", cce.dict())
                
        except Exception as e:
            logger.error(f"Cross Channel Detector processing error: {e}")
