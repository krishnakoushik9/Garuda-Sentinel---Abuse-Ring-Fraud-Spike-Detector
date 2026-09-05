import sqlite3
import logging
from typing import List, Dict
from src.config import SQLITE_DB_PATH
from src.api.deps import get_neo4j

logger = logging.getLogger("network_scorer")

class NetworkRiskPropagator:
    """
    Propagates risk across the transaction network.
    Uses Personalized PageRank on Neo4j GDS, with a complete 
    recursive risk contagion model on SQLite for offline fallback.
    """
    def __init__(self, db_path=None):
        self.db_path = db_path or SQLITE_DB_PATH

    def propagate_risk(self, known_mules: List[str]) -> Dict[str, float]:
        """
        Runs Personalized PageRank in Neo4j GDS if available,
        otherwise runs local SQLite contagious risk propagation.
        """
        propagated_scores = {}
        
        # 1. Try Neo4j GDS
        neo4j_online = False
        try:
            driver = next(get_neo4j())
            if driver:
                with driver.session() as session:
                    # Verify if GDS projection 'fraud_graph' exists
                    # If not, run standard stream query or fallback
                    cypher = """
                        CALL gds.pageRank.stream('fraud_graph', {
                            maxIterations: 20,
                            dampingFactor: 0.85,
                            sourceNodes: [
                                (a:Account) WHERE a.id IN $known_mules | id(a)
                            ]
                        })
                        YIELD nodeId, score
                        WITH gds.util.asNode(nodeId) AS account, score
                        WHERE score > 0.01
                        SET account.propagated_risk = score
                        RETURN account.id as id, score
                        ORDER BY score DESC
                    """
                    records = session.run(cypher, known_mules=known_mules).data()
                    for r in records:
                        propagated_scores[r["id"]] = round(r["score"], 4)
                neo4j_online = True
        except Exception:
            pass

        # 2. Resilient SQLite local recursion fallback
        if not neo4j_online:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                # Direct mules get 1.0
                for mule in known_mules:
                    propagated_scores[mule] = 1.0
                
                # 1st-Hop Neighbors
                hop1_accounts = set()
                for mule in known_mules:
                    cursor.execute("""
                        SELECT DISTINCT receiver_account as neighbor FROM transactions WHERE sender_account = ?
                        UNION
                        SELECT DISTINCT sender_account as neighbor FROM transactions WHERE receiver_account = ?
                    """, (mule, mule))
                    for r in cursor.fetchall():
                        n = r["neighbor"]
                        if n not in propagated_scores:
                            hop1_accounts.add(n)
                            propagated_scores[n] = 0.55  # Hop 1 gets >0.3 automatically
                
                # 2nd-Hop Neighbors
                for h1 in list(hop1_accounts):
                    cursor.execute("""
                        SELECT DISTINCT receiver_account as neighbor FROM transactions WHERE sender_account = ?
                        UNION
                        SELECT DISTINCT sender_account as neighbor FROM transactions WHERE receiver_account = ?
                    """, (h1, h1))
                    for r in cursor.fetchall():
                        n = r["neighbor"]
                        if n not in propagated_scores:
                            propagated_scores[n] = 0.35  # Hop 2 gets >0.3 automatically

            except Exception as e:
                logger.error(f"Local SQLite risk propagation failed: {e}")
            finally:
                conn.close()

        return propagated_scores

    def get_contamination_radius(self, mule_account_id: str) -> dict:
        """
        Computes the contamination profile (risk hop metrics) for a suspect mule.
        """
        hop1_count = 0
        hop2_count = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get hop 1 accounts
            cursor.execute("""
                SELECT DISTINCT receiver_account FROM transactions WHERE sender_account = ?
                UNION
                SELECT DISTINCT sender_account FROM transactions WHERE receiver_account = ?
            """, (mule_account_id, mule_account_id))
            hop1_nodes = [r[0] for r in cursor.fetchall()]
            hop1_count = len(hop1_nodes)
            
            # Get hop 2 accounts excluding hop 1 and original mule
            if hop1_nodes:
                placeholders = ",".join("?" for _ in hop1_nodes)
                # Select distinct neighbors of hop 1 nodes
                query = f"""
                    SELECT DISTINCT receiver_account FROM transactions WHERE sender_account IN ({placeholders})
                    UNION
                    SELECT DISTINCT sender_account FROM transactions WHERE receiver_account IN ({placeholders})
                """
                cursor.execute(query, hop1_nodes + hop1_nodes)
                hop2_nodes = [r[0] for r in cursor.fetchall()]
                
                exclude = set(hop1_nodes)
                exclude.add(mule_account_id)
                hop2_nodes = [n for n in hop2_nodes if n not in exclude]
                hop2_count = len(hop2_nodes)
                
        except Exception as e:
            logger.error(f"Failed to fetch contamination radius for {mule_account_id}: {e}")
        finally:
            conn.close()
            
        return {
            "mule_account_id": mule_account_id,
            "hop_1_contacts": hop1_count,
            "hop_2_contacts": hop2_count,
            "total_threat_radius": hop1_count + hop2_count
        }
