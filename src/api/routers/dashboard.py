from fastapi import APIRouter, Depends
import sqlite3
from src.api.deps import get_db, get_neo4j
from src.api.models.schemas import DashboardSummary
from neo4j import GraphDatabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: sqlite3.Connection = Depends(get_db), driver: GraphDatabase = Depends(get_neo4j)):
    # Counts
    accounts = db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    txns = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    high_risk = db.execute("SELECT COUNT(*) FROM transactions WHERE risk_score > 0.7").fetchone()[0]
    mule_count = db.execute("SELECT COUNT(DISTINCT account_id) FROM mule_accounts").fetchone()[0]
    
    # Fraud patterns
    patterns_rows = db.execute("""
        SELECT fraud_type, COUNT(*) as count 
        FROM fraud_events 
        GROUP BY fraud_type 
        ORDER BY count DESC
    """).fetchall()
    top_patterns = [dict(row) for row in patterns_rows]
    
    # Recent alerts
    alerts_rows = db.execute("""
        SELECT f.event_id as id, f.transaction_id, f.account_id, f.fraud_type, f.severity, f.detected_at as timestamp,
               t.amount, t.risk_score, t.channel
        FROM fraud_events f
        LEFT JOIN transactions t ON f.transaction_id = t.transaction_id
        ORDER BY f.detected_at DESC LIMIT 5
    """).fetchall()
    recent_alerts = [dict(row) for row in alerts_rows]
    
    # Graph stats
    communities = db.execute("SELECT COUNT(DISTINCT community_id) FROM graph_analytics").fetchone()[0]
    
    return {
        "total_accounts": accounts,
        "total_transactions": txns,
        "high_risk_count": high_risk,
        "mule_count": mule_count,
        "top_fraud_patterns": top_patterns,
        "recent_alerts": recent_alerts,
        "graph_stats": {
            "communities": communities,
            "neo4j_online": driver is not None
        }
    }
