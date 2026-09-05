import json
import os
import pandas as pd
from kafka import KafkaConsumer
from src.models.xgboost_scorer import XGBoostScorer
from src.agents.orchestrator import FraudOrchestrator
from src.pipeline.feature_engineering import FeatureEngineer

class FraudScoringConsumer:
    def __init__(self, bootstrap_servers=None):
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_SERVERS", "localhost:9092")
        self.scorer = XGBoostScorer()
        self.orchestrator = FraudOrchestrator()
        self.engineer = FeatureEngineer()
        
        try:
            self.consumer = KafkaConsumer(
                'boi_transactions',
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=False,
                group_id='fraud_detection_group'
            )
            self.enabled = True
        except Exception as e:
            print(f"Kafka Consumer failed to connect: {e}. Running in dummy mode.")
            self.enabled = False

    def consume_loop(self):
        if not self.enabled:
            print("Kafka Consumer disabled. Exiting consume loop.")
            return

        print("Starting consumption from boi_transactions...")
        for message in self.consumer:
            tx = message.value
            self.process_transaction(tx)
            self.consumer.commit()

    def process_transaction(self, tx: dict):
        # 1. Compute real features from actual transaction data
        features = self.engineer.compute_features(
            account_id=tx['sender_account'],
            transaction=tx
        )
        feature_array = features.to_array()  # numpy array
        
        feature_df = pd.DataFrame([feature_array], columns=[
            'amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag',
            'night_txn_ratio', 'txn_velocity_1h', 'txn_velocity_24h', 'txn_velocity_7d',
            'unique_beneficiaries_7d', 'graph_degree_centrality', 'suspicious_neighbor_count', 'hop_2_mule_count'
        ])
        
        # 2. Score with XGBoost
        score = self.scorer.score(feature_df)[0]
        
        if score > 0.7:
            print(f"ALERT: High risk transaction {tx['transaction_id']} (Score: {score:.4f})")
            # 3. Route to agent orchestrator for deep investigation
            result = self.orchestrator.run_investigation(
                tx['transaction_id'], 
                tx['sender_account'], 
                feature_df.iloc[0].to_dict()
            )
            print(f"Investigation Result: {result['final_verdict']} - {result.get('explanation_narrative', '')}")
        else:
            print(f"Transaction {tx['transaction_id']} cleared (Score: {score:.4f})")

if __name__ == "__main__":
    print("--- FraudScoringConsumer Demo ---")
    consumer = FraudScoringConsumer()
    # Mocking one transaction process
    mock_tx = {
        'transaction_id': 'TXN_KAFKA_TEST',
        'sender_account': 'ACC000001',
        'receiver_account': 'ACC000002',
        'amount': 95000.0,
        'timestamp': '2026-05-29 15:00:00'
    }
    consumer.process_transaction(mock_tx)
