import os
import redis
from src.agents.state import FraudInvestigationState

class BehavioralAgent:
    def __init__(self, redis_host='localhost', redis_port=6379):
        try:
            self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            self.redis.ping()
            self.use_redis = True
        except:
            self.use_redis = False

    def investigate(self, state: FraudInvestigationState) -> FraudInvestigationState:
        findings = []
        score = 0.0
        features = state['features']
        
        # 1. Velocity Analysis
        v1h = features.get('txn_velocity_1h', 0)
        v24h = features.get('txn_velocity_24h', 0)
        
        if v1h > 10:
            findings.append(f"Extreme 1h velocity: {v1h} transactions.")
            score += 0.5
        elif v1h > 5:
            findings.append(f"Elevated 1h velocity: {v1h} transactions.")
            score += 0.2
            
        # 2. Amount Deviation
        zscore = abs(features.get('amount_zscore', 0))
        if zscore > 3:
            findings.append(f"Significant amount deviation (Z-score: {zscore:.2f})")
            score += 0.3
            
        # 3. New Beneficiary with high amount
        if features.get('is_new_beneficiary') and features.get('amount', 0) > 50000:
            findings.append("High-value transfer to new beneficiary.")
            score += 0.4

        state['behavioral_score'] = min(1.0, score)
        state['behavioral_findings'] = findings
        return state

if __name__ == "__main__":
    print("--- BehavioralAgent Demo ---")
    agent = BehavioralAgent()
    mock_state = {
        'features': {'txn_velocity_1h': 12, 'amount_zscore': 4.5, 'is_new_beneficiary': True, 'amount': 75000},
        'metadata': {}
    }
    result = agent.investigate(mock_state)
    print("Score:", result['behavioral_score'])
    print("Findings:", result['behavioral_findings'])
