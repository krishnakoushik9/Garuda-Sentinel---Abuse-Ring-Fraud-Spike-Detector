from typing import TypedDict, List, Dict, Any, Optional

class FraudInvestigationState(TypedDict):
    transaction_id: str
    account_id: str
    
    # Feature inputs
    features: Dict[str, Any]
    
    # Agent scores (0.0 to 1.0)
    graph_score: float
    temporal_score: float
    behavioral_score: float
    
    # Findings
    graph_findings: List[str]
    temporal_findings: List[str]
    behavioral_findings: List[str]
    
    # GNN embeddings
    gnn_embedding: Optional[List[float]]
    
    # Final outputs
    final_risk_score: float
    final_verdict: str  # mule_confirmed, suspicious, cleared
    explanation_narrative: str
    
    # Context
    shap_values: Optional[Dict[str, float]]
    metadata: Dict[str, Any]
