import os
import torch
from neo4j import GraphDatabase
from src.agents.state import FraudInvestigationState
from src.models.graph_sage import MuleDetectionGNN, build_transaction_graph
from src.pipeline.cobol_bridge import get_account_transactions
from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

MODEL_PATH = "models/gnn_mule.pt"
_model = None

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _model = MuleDetectionGNN(in_channels=12, hidden_channels=64, out_channels=2)
                _model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
                _model.eval()
            except Exception as e:
                print(f"Error loading GNN model: {e}")
    return _model

RELAY_MULE_QUERY = """
MATCH (m:Account) WHERE m.account_id = $account_id OR m.id = $account_id
MATCH (m)<-[:SENT_TO]-(src)
MATCH (m)-[:SENT_TO]->(dst)
RETURN count(*) as relay_count
"""

FAN_OUT_QUERY = """
MATCH (m:Account) WHERE m.account_id = $account_id OR m.id = $account_id
MATCH (m)-[:SENT_TO]->(dst)
RETURN count(DISTINCT dst) as fan_out_count
"""

HOP_2_MULE_QUERY = """
MATCH (m:Account) WHERE m.account_id = $account_id OR m.id = $account_id
MATCH (m)-[:SENT_TO*2]->(target)
RETURN count(DISTINCT target) as hop2_mules
"""

class GraphAgent:
    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.enabled = True
        except Exception:
            self.enabled = False

    def investigate(self, state: FraudInvestigationState) -> FraudInvestigationState:
        account_id = state['account_id']
        
        # 1. Neo4j queries
        relay_count = 0
        fan_out_destinations = 0
        hop2_count = 0
        
        if self.enabled:
            try:
                with self.driver.session() as session:
                    relay_res = session.run(RELAY_MULE_QUERY, account_id=account_id).single()
                    relay_count = relay_res['relay_count'] if relay_res else 0
                    
                    fan_out_res = session.run(FAN_OUT_QUERY, account_id=account_id).single()
                    fan_out_destinations = fan_out_res['fan_out_count'] if fan_out_res else 0
                    
                    hop2_res = session.run(HOP_2_MULE_QUERY, account_id=account_id).single()
                    hop2_count = hop2_res['hop2_mules'] if hop2_res else 0
            except Exception as e:
                print(f"Neo4j investigation query error: {e}")
                
        # 2. GNN inference
        model = get_model()
        mule_similarity = 0.05
        if model is not None:
            try:
                txns = get_account_transactions(account_id, n=50)
                if len(txns) > 0:
                    graph_data = build_transaction_graph(txns)
                    with torch.no_grad():
                        embedding = model.get_embedding(graph_data.x, graph_data.edge_index)
                        mule_similarity = float(torch.sigmoid(embedding.mean()).item())
            except Exception as e:
                print(f"GNN inference error in agent: {e}")
                
        # 3. Calculate score
        score = 0.05
        if relay_count > 0:
            score += 0.3
        if fan_out_destinations > 5:
            score += 0.2
        if hop2_count > 2:
            score += 0.3
        score += mule_similarity * 0.4
        
        state['graph_score'] = min(1.0, score)
        state['graph_findings'] = {
            "relay_pattern_detected": relay_count > 0,
            "fan_out_count": fan_out_destinations,
            "hop_2_mule_count": hop2_count,
            "mule_embedding_similarity": mule_similarity,
        }
        return state

async def graph_intelligence_agent(state):
    agent = GraphAgent()
    return agent.investigate(state)
