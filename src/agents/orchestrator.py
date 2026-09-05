from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.agents.state import FraudInvestigationState
from src.agents.graph_agent import GraphAgent
from src.agents.temporal_agent import TemporalAgent
from src.agents.behavioral_agent import BehavioralAgent
from src.agents.risk_fusion_agent import RiskFusionAgent
from src.agents.explainability_agent import ExplainabilityAgent

class FraudOrchestrator:
    def __init__(self):
        self.graph_agent = GraphAgent()
        self.temporal_agent = TemporalAgent()
        self.behavioral_agent = BehavioralAgent()
        self.fusion_agent = RiskFusionAgent()
        self.explain_agent = ExplainabilityAgent()
        
        self.workflow = self._build_workflow()

    def regulatory_agent(self, state: FraudInvestigationState) -> FraudInvestigationState:
        """Regulatory compliance assessment for high-risk accounts."""
        metadata = state.get('metadata', {})
        metadata['regulatory_status'] = "SAR_REQUIRED"
        metadata['sar_filing_recommended'] = True
        state['metadata'] = metadata
        return state

    def _build_workflow(self):
        builder = StateGraph(FraudInvestigationState)
        
        # Add Nodes
        builder.add_node("graph_analysis", self.graph_agent.investigate)
        builder.add_node("temporal_analysis", self.temporal_agent.investigate)
        builder.add_node("behavioral_analysis", self.behavioral_agent.investigate)
        builder.add_node("risk_fusion", self.fusion_agent.investigate)
        builder.add_node("regulatory_agent", self.regulatory_agent)
        builder.add_node("explainability", self.explain_agent.investigate)
        
        # Define Edges
        builder.set_entry_point("graph_analysis")
        builder.add_edge("graph_analysis", "temporal_analysis")
        builder.add_edge("temporal_analysis", "behavioral_analysis")
        builder.add_edge("behavioral_analysis", "risk_fusion")
        
        # Conditional Edge based on risk score
        builder.add_conditional_edges(
            "risk_fusion",
            lambda state: "regulatory_agent" if state.get('final_risk_score', 0) > 0.5 else "explainability",
            {
                "regulatory_agent": "regulatory_agent",
                "explainability": "explainability"
            }
        )
        builder.add_edge("regulatory_agent", "explainability")
        builder.add_edge("explainability", END)
        
        return builder.compile()

    def run_investigation(self, transaction_id: str, account_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        initial_state = {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "features": features,
            "graph_findings": {},
            "temporal_findings": [],
            "behavioral_findings": [],
            "metadata": {}
        }
        return self.workflow.invoke(initial_state)

if __name__ == "__main__":
    print("--- FraudOrchestrator Demo ---")
    orchestrator = FraudOrchestrator()
    mock_features = {
        'graph_degree_centrality': 0.7,
        'dormancy_break_flag': True,
        'txn_velocity_1h': 15,
        'amount_zscore': 2.5,
        'is_new_beneficiary': True,
        'amount': 100000
    }
    
    result = orchestrator.run_investigation("TXN_DEMO_999", "ACC000001", mock_features)
    print("\nInvestigation Complete")
    print(f"Final Score: {result['final_risk_score']}")
    print(f"Verdict: {result['final_verdict']}")
    print(f"Narrative: {result.get('explanation_narrative', 'N/A')}")
