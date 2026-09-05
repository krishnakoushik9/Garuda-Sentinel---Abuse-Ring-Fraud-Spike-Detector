import json
import logging
from src.config import KAFKA_BOOTSTRAP

logger = logging.getLogger("kafka_client")
logging.basicConfig(level=logging.INFO)

class KafkaPubSub:
    """
    Resilient Kafka wrapper that automatically falls back to an in-memory pub-sub 
    mechanism if the Kafka broker is offline or unreachable.
    """
    _subscribers = {}

    def __init__(self):
        self.producer = None
        self.use_fallback = True
        try:
            from kafka import KafkaProducer
            self.producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BOOTSTRAP],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=1000,
                max_block_ms=1000
            )
            self.use_fallback = False
            logger.info("Kafka: Connected successfully to broker.")
        except Exception as e:
            logger.warning(f"Kafka broker not found or offline ({e}). Operating in resilient memory mode.")

    def publish(self, topic: str, value: dict):
        # Convert any objects (like datetime) to string before serialization if needed,
        # but simulator will pass clean JSON dicts.
        if not self.use_fallback and self.producer:
            try:
                self.producer.send(topic, value)
                self.producer.flush()
                logger.info(f"[Kafka Broker] Published to topic {topic}")
                return
            except Exception as e:
                logger.warning(f"Failed to publish to Kafka ({e}). Defaulting to memory pub-sub.")
        
        # Local fallback execution
        logger.info(f"[Local PubSub] Published to topic {topic}")
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                try:
                    callback(value)
                except Exception as ex:
                    logger.error(f"Subscriber callback error on topic {topic}: {ex}")

    @classmethod
    def subscribe(cls, topic: str, callback):
        if topic not in cls._subscribers:
            cls._subscribers[topic] = []
        cls._subscribers[topic].append(callback)
        logger.info(f"Subscribed callback to memory topic: {topic}")
