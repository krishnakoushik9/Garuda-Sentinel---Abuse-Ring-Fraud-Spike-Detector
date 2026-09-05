from src.agents.state import FraudInvestigationState

class ExplainabilityAgent:
    def investigate(self, state: FraudInvestigationState) -> FraudInvestigationState:
        verdict = state['final_verdict']
        score = state['final_risk_score']
        
        if verdict == "cleared":
            state['explanation_narrative'] = "Transaction analyzed and cleared. No suspicious patterns detected."
            return state
            
        # Parse graph findings dynamically if it is a dictionary or a list
        graph_findings_raw = state.get('graph_findings', {})
        if isinstance(graph_findings_raw, dict):
            graph_findings = []
            if graph_findings_raw.get("relay_pattern_detected"):
                graph_findings.append("Relay pattern detected")
            fan_out = graph_findings_raw.get("fan_out_count", 0)
            if fan_out > 0:
                graph_findings.append(f"Fan-out of {fan_out} destinations")
            hop2 = graph_findings_raw.get("hop_2_mule_count", 0)
            if hop2 > 0:
                graph_findings.append(f"Connected to {hop2} high-risk accounts within 2 hops")
            sim = graph_findings_raw.get("mule_embedding_similarity", 0)
            if sim > 0.5:
                graph_findings.append(f"GNN mule embedding similarity is high ({sim:.2f})")
        else:
            graph_findings = graph_findings_raw or []

        # Build narrative from findings
        all_findings = graph_findings + \
                       state.get('temporal_findings', []) + \
                       state.get('behavioral_findings', [])
        
        # Pull top SHAP factors if available
        shap_narrative = ""
        shap_vals = state.get('shap_values')
        if shap_vals:
            # Sort factors by importance
            sorted_factors = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)
            top_3 = [f[0].replace("_", " ") for f in sorted_factors[:3]]
            shap_narrative = f"The primary risk drivers were {', '.join(top_3)}."

        narrative = f"Account flagged as {verdict.replace('_', ' ')} (Risk Score: {score:.2f}). "
        if shap_narrative:
            narrative += shap_narrative + " "
            
        if all_findings:
            narrative += "Key findings: " + "; ".join(all_findings[:5]) + "."
        else:
            narrative += "Flagged due to anomalous behavior across multiple scoring dimensions."

        state['explanation_narrative'] = narrative
        return state

if __name__ == "__main__":
    print("--- ExplainabilityAgent Demo ---")
    agent = ExplainabilityAgent()
    mock_state = {
        'final_verdict': 'mule_confirmed',
        'final_risk_score': 0.88,
        'graph_findings': {'relay_pattern_detected': True, 'fan_out_count': 5},
        'temporal_findings': ['Dormancy break'],
        'shap_values': {'txn_velocity_1h': 0.5, 'amount_zscore': 0.3, 'is_new_beneficiary': 0.1}
    }
    result = agent.investigate(mock_state)
    print("Narrative:", result['explanation_narrative'])
