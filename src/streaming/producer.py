import json
import os
from kafka import KafkaProducer

class TransactionProducer:
    def __init__(self, bootstrap_servers=None):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_SERVERS", "localhost:9092")
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='lz4',
                linger_ms=5,
                enable_idempotence=True
            )
            self.enabled = True
        except Exception as e:
            print(f"Kafka Producer failed to connect: {e}. Running in dummy mode.")
            self.enabled = False

    def send_transaction(self, transaction: dict):
        if not self.enabled:
            print(f"[DUMMY KAFKA] Sending TXN: {transaction['transaction_id']}")
            return
        
        self.producer.send('boi_transactions', transaction)
        self.producer.flush()

if __name__ == "__main__":
    print("--- TransactionProducer Demo ---")
    producer = TransactionProducer()
    mock_tx = {
        'transaction_id': 'TXN_KAFKA_001',
        'sender_account': 'ACC000001',
        'receiver_account': 'ACC000002',
        'amount': 1200.50,
        'timestamp': '2026-05-29T14:00:00'
    }
    producer.send_transaction(mock_tx)
