from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import sqlite3
from neo4j import GraphDatabase
from src.api.deps import get_db, get_neo4j
from src.api.models.schemas import AccountProfile, GraphNeighborhood, Node, Edge
from src.api.routers.datasource import get_active_source

router = APIRouter(prefix="/accounts", tags=["Accounts"])

@router.get("", response_model=List[AccountProfile])
def get_accounts(
    page: int = 1,
    limit: int = 20,
    risk_score_min: float = 0.0,
    community_id: Optional[str] = None,
    state: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * limit
    source = get_active_source(db)
    prefix = "REAL%" if source == "REGULATORY_FEED" else "ACC%"
    query = """
    SELECT a.*, g.pagerank, g.community_id 
    FROM accounts a
    LEFT JOIN graph_analytics g ON a.account_id = g.account_id
    WHERE a.account_id LIKE ?
    """
    params = [prefix]
    if community_id:
        query += " AND g.community_id = ?"
        params.append(community_id)
    if state:
        query += " AND LOWER(a.state) = LOWER(?)"
        params.append(state)
    
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]

@router.get("/{account_id}", response_model=AccountProfile)
def get_account(account_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("""
        SELECT a.*, g.pagerank, g.community_id 
        FROM accounts a
        LEFT JOIN graph_analytics g ON a.account_id = g.account_id
        WHERE a.account_id = ?
    """, (account_id,)).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    
    data = dict(row)
    # Get last 10 transactions
    txs = db.execute("""
        SELECT * FROM transactions 
        WHERE sender_account = ? OR receiver_account = ? 
        ORDER BY timestamp DESC LIMIT 10
    """, (account_id, account_id)).fetchall()
    data['recent_transactions'] = [dict(tx) for tx in txs]
    
    return data

@router.get("/{account_id}/graph", response_model=GraphNeighborhood)
def get_account_graph(account_id: str, driver: GraphDatabase = Depends(get_neo4j)):
    if not driver:
        return {"nodes": [], "edges": [], "is_offline": True}
    
    query = """
    MATCH (a:Account {id: $account_id})-[:SENT_TO*1..2]-(neighbor:Account)
    RETURN neighbor.id as id, neighbor.risk_score as risk_score, 
           neighbor.is_mule_suspected as is_mule_suspected
    LIMIT 50
    """
    
    with driver.session() as session:
        result = session.run(query, account_id=account_id)
        
        nodes_dict = {}
        # Ensure standard start node is present
        nodes_dict[account_id] = Node(id=account_id, label="Account", properties={})
        
        edges = []
        for record in result:
            neighbor_id = record.get("id")
            if not neighbor_id:
                continue
            
            risk_score = record.get("risk_score")
            is_mule_suspected = record.get("is_mule_suspected")
            
            if neighbor_id not in nodes_dict:
                nodes_dict[neighbor_id] = Node(
                    id=neighbor_id,
                    label="Account",
                    properties={
                        "risk_score": risk_score if risk_score is not None else 0.0,
                        "is_mule_suspected": is_mule_suspected if is_mule_suspected is not None else False
                    }
                )
            
            edges.append(
                Edge(
                    source=account_id,
                    target=neighbor_id,
                    type="SENT_TO",
                    properties={}
                )
            )
            
        return {"nodes": list(nodes_dict.values()), "edges": edges}


@router.post("/{account_id}/flag")
def flag_account(account_id: str, driver: GraphDatabase = Depends(get_neo4j), db: sqlite3.Connection = Depends(get_db)):
    # Update SQLite
    db.execute("UPDATE accounts SET status = 'FLAGGED' WHERE account_id = ?", (account_id,))
    db.commit()
    
    # Update Neo4j
    if driver:
        with driver.session() as session:
            session.run("MATCH (a:Account {account_id: $aid}) SET a.status = 'FLAGGED'", aid=account_id)
            
    return {"status": "success", "message": f"Account {account_id} flagged."}
