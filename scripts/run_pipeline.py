import os
import json
from src.pipeline.cobol_bridge import CobolBridge
from src.pipeline.feature_engineering import FeatureEngineer
from src.models.xgboost_scorer import XGBoostScorer
from src.agents.orchestrator import FraudOrchestrator
import pandas as pd

def run_demo():
    print("=== BOI Fraud Intelligence Platform Demo ===")
    
    # 1. Load Data
    bridge = CobolBridge()
    fe = FeatureEngineer()
    scorer = XGBoostScorer()
    orchestrator = FraudOrchestrator()
    
    try:
        tx_df = bridge.fetch_transactions(limit=100)
        history = bridge.fetch_transactions(limit=1000)
        print(f"Loaded {len(tx_df)} latest transactions.")
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return

    # 2. Pick a suspicious-looking transaction to demo
    # In a real run, we would loop through all
    sample_tx = tx_df.iloc[0].to_dict()
    print(f"\nAnalyzing Transaction: {sample_tx['transaction_id']}")
    print(f"From: {sample_tx['sender_account']} To: {sample_tx['receiver_account']} Amount: {sample_tx['amount']}")
    
    # 3. Feature Engineering
    features = fe.compute_features(sample_tx, history)
    feature_df = pd.DataFrame([features.__dict__])
    # Match scorer columns
    cols = [
        'amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag',
        'night_txn_ratio', 'txn_velocity_1h', 'txn_velocity_24h', 'txn_velocity_7d',
        'unique_beneficiaries_7d', 'graph_degree_centrality', 'suspicious_neighbor_count', 'hop_2_mule_count'
    ]
    X = feature_df[cols]
    
    # 4. Initial Scoring
    score = scorer.score(X)[0]
    print(f"XGBoost Fraud Score: {score:.4f}")
    
    # 5. Deep Agentic Investigation
    print("\nTriggering LangGraph Agent Investigation...")
    # Inject SHAP values for demo purposes if we don't have a real model trained yet
    investigation_result = orchestrator.run_investigation(
        sample_tx['transaction_id'], 
        sample_tx['sender_account'], 
        X.iloc[0].to_dict()
    )
    
    print("\n--- INVESTIGATION REPORT ---")
    print(f"Final Risk Score: {investigation_result['final_risk_score']}")
    print(f"Verdict: {investigation_result['final_verdict'].upper()}")
    print(f"Narrative: {investigation_result['explanation_narrative']}")
    
    print("\n--- DETAILED FINDINGS ---")
    print("Graph:", investigation_result.get('graph_findings'))
    print("Temporal:", investigation_result.get('temporal_findings'))
    print("Behavioral:", investigation_result.get('behavioral_findings'))

if __name__ == "__main__":
    run_demo()
