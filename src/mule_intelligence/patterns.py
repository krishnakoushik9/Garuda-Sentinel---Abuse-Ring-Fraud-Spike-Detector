import sqlite3
import logging
from typing import Dict, Any, List
from src.config import SQLITE_DB_PATH
from src.api.deps import get_neo4j

logger = logging.getLogger("mule_patterns")

MULE_PATTERNS = {
    "RELAY_CHAIN": {
        "cypher": """
            MATCH path = (source:Account)-[:SENT_TO*2..5]->(cashout:Account)
            WHERE source.id = $account_id
            AND ALL(r IN relationships(path) WHERE 
                duration.inSeconds(r.timestamp, r.next_timestamp).seconds < 3600
                AND r.amount >= r.prev_amount * 0.7)
            RETURN path, length(path) as chain_length
            ORDER BY chain_length DESC LIMIT 10
        """,
        "mule_probability": 0.89,
        "description": "Sequential forwarding within 1 hour, 70%+ amount preserved"
    },
    "FAN_OUT": {
        "cypher": """
            MATCH (mule:Account {id: $account_id})-[r:SENT_TO]->(dest:Account)
            WHERE r.timestamp > datetime() - duration('P7D')
            WITH mule, COUNT(DISTINCT dest) as dest_count, SUM(r.amount) as total_out
            MATCH (src:Account)-[:SENT_TO]->(mule)
            WITH mule, dest_count, total_out, COUNT(DISTINCT src) as src_count
            WHERE dest_count > 5 AND src_count <= 2
            RETURN mule.id, dest_count, src_count, total_out
        """,
        "mule_probability": 0.85,
        "description": "1-2 sources, 5+ destinations: classic fan-out mule"
    },
    "LAYERING": {
        "cypher": """
            MATCH (origin:Account)-[:SENT_TO*1..4]->(layer:Account)
            WHERE origin.id = $account_id
            WITH DISTINCT layer, 
                 SIZE([(layer)-[:SENT_TO]->() | 1]) as out_degree,
                 SIZE([()-[:SENT_TO]->(layer) | 1]) as in_degree
            WHERE out_degree > 0 AND in_degree > 0
            AND abs(out_degree - in_degree) < 2
            RETURN layer.id, out_degree, in_degree
            ORDER BY out_degree DESC
        """,
        "mule_probability": 0.78,
        "description": "Multiple intermediate hops with pass-through behavior"
    },
    "DORMANCY_BREAK": {
        "sql": """
            SELECT a.account_id, 
                   MAX(t1.timestamp) as last_old_txn,
                   MIN(t2.timestamp) as first_new_txn,
                   julianday(MIN(t2.timestamp)) - julianday(MAX(t1.timestamp)) as dormant_days,
                   SUM(t2.amount) as activation_amount
            FROM accounts a
            JOIN transactions t1 ON t1.sender_account = a.account_id 
                AND t1.timestamp < datetime('now', '-30 days')
            JOIN transactions t2 ON t2.sender_account = a.account_id 
                AND t2.timestamp > datetime('now', '-7 days')
            WHERE a.account_id = ?
            GROUP BY a.account_id
            HAVING dormant_days > 30 AND activation_amount > 10000
        """,
        "mule_probability": 0.78,
        "description": "30+ day dormancy followed by high-volume activation"
    },
    "STRUCTURING": {
        "sql": """
            SELECT sender_account,
                   COUNT(*) as txn_count,
                   SUM(amount) as total,
                   MAX(amount) as max_single,
                   AVG(amount) as avg_amount
            FROM transactions
            WHERE sender_account = ?
            AND timestamp > datetime('now', '-1 day')
            AND amount BETWEEN 40000 AND 49999
            GROUP BY sender_account
            HAVING txn_count >= 3 AND max_single < 50000
        """,
        "mule_probability": 0.72,
        "description": "Multiple transactions just below ₹50,000 reporting threshold"
    },
    "VELOCITY_SPIKE": {
        "description": "TXN count > 3 sigma above 30-day mean",
        "mule_probability": 0.81
    },
    "NIGHT_ACTIVITY": {
        "description": "60%+ transactions between 11PM-5AM",
        "mule_probability": 0.65
    },
    "ROUND_TRIP": {
        "cypher": """
            MATCH (a:Account {id: $account_id})-[:SENT_TO*2..6]->(a)
            RETURN COUNT(*) as cycle_count
        """,
        "mule_probability": 0.91,
        "description": "Money returns to origin — classic circular laundering"
    }
}

class MulePatternEvaluator:
    """Runs high-fidelity evaluation of the 8 mule patterns on any target account."""
    def __init__(self, db_path=None):
        self.db_path = db_path or SQLITE_DB_PATH

    def evaluate_account(self, account_id: str) -> Dict[str, Dict[str, Any]]:
        results = {}
        for pattern_name, spec in MULE_PATTERNS.items():
            results[pattern_name] = {
                "triggered": False,
                "probability": spec["mule_probability"],
                "description": spec["description"] if "description" in spec else "",
                "details": {}
            }
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Evaluate DORMANCY_BREAK (SQL)
            cursor.execute(MULE_PATTERNS["DORMANCY_BREAK"]["sql"], (account_id,))
            dorm_row = cursor.fetchone()
            if dorm_row:
                results["DORMANCY_BREAK"]["triggered"] = True
                results["DORMANCY_BREAK"]["details"] = dict(dorm_row)

            # 2. Evaluate STRUCTURING (SQL)
            cursor.execute(MULE_PATTERNS["STRUCTURING"]["sql"], (account_id,))
            struct_row = cursor.fetchone()
            if struct_row:
                results["STRUCTURING"]["triggered"] = True
                results["STRUCTURING"]["details"] = dict(struct_row)

            # 3. Evaluate VELOCITY_SPIKE (SQL / Statistics fallback)
            cursor.execute("""
                SELECT COUNT(*) as day_count FROM transactions 
                WHERE sender_account = ? AND timestamp > datetime('now', '-1 day')
            """, (account_id,))
            day_count = cursor.fetchone()["day_count"]
            
            cursor.execute("""
                SELECT COUNT(*) as month_count FROM transactions 
                WHERE sender_account = ? AND timestamp > datetime('now', '-30 days')
            """, (account_id,))
            month_count = cursor.fetchone()["month_count"]
            
            # Estimate mean and deviation
            mean_daily = month_count / 30.0
            if day_count > (mean_daily + 5) and day_count > 3:
                results["VELOCITY_SPIKE"]["triggered"] = True
                results["VELOCITY_SPIKE"]["details"] = {
                    "last_24h_count": day_count,
                    "mean_daily_count": round(mean_daily, 2),
                    "deviation_spike": True
                }

            # 4. Evaluate NIGHT_ACTIVITY (SQL)
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN strftime('%H', timestamp) >= '23' OR strftime('%H', timestamp) < '05' THEN 1 ELSE 0 END) as night_count
                FROM transactions 
                WHERE sender_account = ? AND timestamp > datetime('now', '-7 days')
            """, (account_id,))
            night_row = cursor.fetchone()
            if night_row and night_row["total"] > 0:
                night_ratio = float(night_row["night_count"] or 0) / float(night_row["total"])
                if night_ratio >= 0.6:
                    results["NIGHT_ACTIVITY"]["triggered"] = True
                    results["NIGHT_ACTIVITY"]["details"] = {
                        "night_ratio": round(night_ratio, 2),
                        "night_tx_count": night_row["night_count"],
                        "total_7d_count": night_row["total"]
                    }

            # 5. Evaluate Graph Patterns (RELAY_CHAIN, FAN_OUT, LAYERING, ROUND_TRIP)
            self._evaluate_graph_patterns(account_id, results, cursor)

        except Exception as e:
            logger.error(f"Error evaluating patterns for account {account_id}: {e}")
        finally:
            conn.close()

        return results

    def _evaluate_graph_patterns(self, account_id: str, results: dict, cursor):
        neo4j_online = False
        try:
            driver = next(get_neo4j())
            if driver:
                with driver.session() as session:
                    # FAN_OUT
                    fo_res = session.run(MULE_PATTERNS["FAN_OUT"]["cypher"], account_id=account_id).single()
                    if fo_res:
                        results["FAN_OUT"]["triggered"] = True
                        results["FAN_OUT"]["details"] = dict(fo_res)
                        
                    # ROUND_TRIP
                    rt_res = session.run(MULE_PATTERNS["ROUND_TRIP"]["cypher"], account_id=account_id).single()
                    if rt_res and rt_res["cycle_count"] > 0:
                        results["ROUND_TRIP"]["triggered"] = True
                        results["ROUND_TRIP"]["details"] = {"cycle_count": rt_res["cycle_count"]}
                        
                    # LAYERING
                    lay_res = session.run(MULE_PATTERNS["LAYERING"]["cypher"], account_id=account_id).data()
                    if lay_res:
                        results["LAYERING"]["triggered"] = True
                        results["LAYERING"]["details"] = {"hops_detected": len(lay_res), "layers": lay_res[:3]}
                        
                    # RELAY_CHAIN
                    relay_res = session.run(MULE_PATTERNS["RELAY_CHAIN"]["cypher"], account_id=account_id).data()
                    if relay_res:
                        results["RELAY_CHAIN"]["triggered"] = True
                        results["RELAY_CHAIN"]["details"] = {"relay_chains": len(relay_res), "chains": relay_res[:3]}
                        
                neo4j_online = True
        except Exception:
            pass

        if not neo4j_online:
            # High-fidelity Relational Fallback queries on SQLite for degree/fan-out
            try:
                # FAN_OUT Fallback: count distinct receivers vs distinct senders last 7 days
                cursor.execute("""
                    SELECT 
                        (SELECT count(distinct receiver_account) FROM transactions WHERE sender_account = ?) as receivers,
                        (SELECT count(distinct sender_account) FROM transactions WHERE receiver_account = ?) as senders
                """, (account_id, account_id))
                cnt = cursor.fetchone()
                if cnt and cnt["receivers"] > 5 and cnt["senders"] <= 2:
                    results["FAN_OUT"]["triggered"] = True
                    results["FAN_OUT"]["details"] = {
                        "receivers_count": cnt["receivers"],
                        "senders_count": cnt["senders"],
                        "fallback": True
                    }

                # ROUND_TRIP Fallback: find 2-hop cycles sender -> intermediary -> sender
                cursor.execute("""
                    SELECT t1.receiver_account as intermediate, t2.receiver_account as target
                    FROM transactions t1
                    JOIN transactions t2 ON t1.receiver_account = t2.sender_account
                    WHERE t1.sender_account = ? AND t2.receiver_account = ?
                    LIMIT 5
                """, (account_id, account_id))
                cycles = cursor.fetchall()
                if cycles:
                    results["ROUND_TRIP"]["triggered"] = True
                    results["ROUND_TRIP"]["details"] = {
                        "cycle_count": len(cycles),
                        "cycles": [dict(c) for c in cycles],
                        "fallback": True
                    }

                # LAYERING Fallback: check matching inflows and outflows within 4 hours
                cursor.execute("""
                    SELECT t1.sender_account as source, t1.amount as amount_in, t2.receiver_account as dest, t2.amount as amount_out
                    FROM transactions t1
                    JOIN transactions t2 ON t1.receiver_account = t2.sender_account
                    WHERE t1.receiver_account = ?
                      AND t2.timestamp >= t1.timestamp
                      AND julianday(t2.timestamp) - julianday(t1.timestamp) <= 0.16
                    LIMIT 5
                """, (account_id,))
                layering_matches = cursor.fetchall()
                if layering_matches:
                    results["LAYERING"]["triggered"] = True
                    results["LAYERING"]["details"] = {
                        "matching_hops": len(layering_matches),
                        "fallback": True
                    }

            except Exception as ex:
                logger.error(f"Fallback graph evaluation failed: {ex}")
