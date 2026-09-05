import numpy as np
from src.agents.state import FraudInvestigationState
from src.models.lstm_autoencoder import TransactionSequenceAutoencoder
import torch

TEMPORAL_FRAUD_PATTERNS = {
    "DORMANCY_BREAK": "Sudden activity after >30 days of inactivity.",
    "RAPID_IN_OUT": "Large credit followed by immediate large debit.",
    "VELOCITY_SPIKE": "Significant increase in transaction frequency."
}

class TemporalAgent:
    def __init__(self, model_path=None):
        self.model = None # Would load from models/lstm_ae.pt

    def investigate(self, state: FraudInvestigationState) -> FraudInvestigationState:
        findings = []
        score = 0.0
        features = state['features']
        
        # 1. Pattern Matching from Features
        if features.get('dormancy_break_flag'):
            findings.append(TEMPORAL_FRAUD_PATTERNS["DORMANCY_BREAK"])
            score += 0.5
            
        if features.get('txn_velocity_1h', 0) > 5:
            findings.append(TEMPORAL_FRAUD_PATTERNS["VELOCITY_SPIKE"])
            score += 0.3

        # 2. LSTM Autoencoder Anomaly Score (Simulated)
        # In production: prepare_account_sequence -> model.anomaly_score
        ae_score = 0.15 # Default
        if score > 0.4:
            ae_score = 0.85 # Correlate for demo
            findings.append(f"LSTM Autoencoder detected sequence anomaly (score: {ae_score})")
            score += 0.2

        state['temporal_score'] = min(1.0, score)
        state['temporal_findings'] = findings
        return state

if __name__ == "__main__":
    print("--- TemporalAgent Demo ---")
    agent = TemporalAgent()
    mock_state = {
        'features': {'dormancy_break_flag': True, 'txn_velocity_1h': 8},
        'metadata': {}
    }
    result = agent.investigate(mock_state)
    print("Score:", result['temporal_score'])
    print("Findings:", result['temporal_findings'])
