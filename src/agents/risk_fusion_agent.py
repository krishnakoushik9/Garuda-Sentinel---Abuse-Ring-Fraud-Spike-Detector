from src.agents.state import FraudInvestigationState

class RiskFusionAgent:
    def __init__(self, weights=None):
        # Default weights for different analysis layers
        self.weights = weights or {
            'graph': 0.4,
            'temporal': 0.3,
            'behavioral': 0.3
        }

    def investigate(self, state: FraudInvestigationState) -> FraudInvestigationState:
        # Calculate weighted average
        gs = state.get('graph_score', 0.0)
        ts = state.get('temporal_score', 0.0)
        bs = state.get('behavioral_score', 0.0)
        
        final_score = (
            gs * self.weights['graph'] +
            ts * self.weights['temporal'] +
            bs * self.weights['behavioral']
        )
        
        # Determine verdict
        if final_score > 0.8:
            verdict = "mule_confirmed"
        elif final_score > 0.4:
            verdict = "suspicious"
        else:
            verdict = "cleared"
            
        state['final_risk_score'] = round(final_score, 4)
        state['final_verdict'] = verdict
        return state

if __name__ == "__main__":
    print("--- RiskFusionAgent Demo ---")
    agent = RiskFusionAgent()
    mock_state = {
        'graph_score': 0.9,
        'temporal_score': 0.7,
        'behavioral_score': 0.8
    }
    result = agent.investigate(mock_state)
    print("Final Risk Score:", result['final_risk_score'])
    print("Final Verdict:", result['final_verdict'])
