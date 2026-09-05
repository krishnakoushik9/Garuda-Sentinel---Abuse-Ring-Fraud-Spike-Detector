from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Transaction(BaseModel):
    transaction_id: str
    timestamp: str
    sender_account: str
    receiver_account: str
    amount: float
    channel: str
    status: str
    description: Optional[str] = None
    risk_score: float = 0.0

class TransactionStats(BaseModel):
    total_count: int
    fraud_count: int
    mule_count: int
    avg_risk_score: float

class AccountProfile(BaseModel):
    account_id: str
    name: str
    customer_segment: str
    city: str
    state: Optional[str] = None
    risk_profile: str
    balance: float
    pagerank: float = 0.0
    community_id: Optional[str] = None
    recent_transactions: List[Transaction] = []

class Node(BaseModel):
    id: str
    label: str
    properties: Dict[str, Any]

class Edge(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]

class GraphNeighborhood(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    is_offline: bool = False

class InvestigationResult(BaseModel):
    investigation_id: str
    status: str
    verdict: Optional[str] = None
    final_risk_score: Optional[float] = None
    explanation: Optional[str] = None
    graph_findings: List[str] = []
    shap_values: Dict[str, float] = {}

class Alert(BaseModel):
    id: str
    transaction_id: str
    account_id: str
    fraud_type: str
    severity: str
    timestamp: str
    amount: Optional[float] = 0.0
    risk_score: Optional[float] = 0.0
    channel: Optional[str] = "N/A"
    description: Optional[str] = None

class DashboardSummary(BaseModel):
    total_accounts: int
    total_transactions: int
    high_risk_count: int
    mule_count: int
    top_fraud_patterns: List[Dict[str, Any]]
    recent_alerts: List[Alert]
    graph_stats: Dict[str, Any]
