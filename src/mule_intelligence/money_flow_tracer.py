import sqlite3
import logging
from typing import Dict, Any, List, Set
from src.config import SQLITE_DB_PATH
from src.api.deps import get_neo4j

logger = logging.getLogger("money_flow_tracer")

class MoneyFlowTracer:
    """
    Traces the upstream and downstream flows of stolen/suspicious funds.
    Enables deep network tracing of relay paths and terminal cash-out locations.
    """
    def __init__(self, db_path=None):
        self.db_path = db_path or SQLITE_DB_PATH

    def trace_downstream(self, account_id: str, max_hops: int = 6) -> dict:
        """
        Traces downstream transfers originating from account_id.
        Identifies intermediate relay layers and final cash-out terminals.
        """
        nodes = {account_id: {"id": account_id, "role": "ORIGIN", "amount_received": 0.0, "amount_forwarded": 0.0}}
        edges = []
        cash_out_points = []
        total_amount_traced = 0.0

        # Try Neo4j first, fallback to SQLite BFS
        neo4j_online = False
        try:
            driver = next(get_neo4j())
            if driver:
                with driver.session() as session:
                    # Traversal
                    cypher = """
                        MATCH path = (start:Account {id: $account_id})-[:SENT_TO*1..6]->(end:Account)
                        RETURN [n IN nodes(path) | n.id] as node_ids,
                               [r IN relationships(path) | {amount: r.amount, channel: r.channel, timestamp: r.timestamp}] as rels
                        LIMIT 50
                    """
                    records = session.run(cypher, account_id=account_id).data()
                    for r in records:
                        nids = r["node_ids"]
                        rels = r["rels"]
                        for i in range(len(rels)):
                            src, dst = nids[i], nids[i+1]
                            amt = rels[i]["amount"]
                            ch = rels[i]["channel"]
                            ts = rels[i]["timestamp"]
                            
                            if src not in nodes:
                                nodes[src] = {"id": src, "role": "RELAY", "amount_received": 0.0, "amount_forwarded": 0.0}
                            if dst not in nodes:
                                nodes[dst] = {"id": dst, "role": "RELAY", "amount_received": 0.0, "amount_forwarded": 0.0}
                                
                            nodes[src]["amount_forwarded"] += amt
                            nodes[dst]["amount_received"] += amt
                            
                            edges.append({
                                "source": src,
                                "target": dst,
                                "amount": amt,
                                "channel": ch,
                                "timestamp": ts
                            })
                            
                            if i == 0:
                                total_amount_traced += amt
                    
                    # Update roles based on out-degree in Neo4j
                    for nid in nodes:
                        if nid == account_id:
                            continue
                        res = session.run("MATCH (a:Account {id: $nid}) RETURN EXISTS((a)-[:SENT_TO]->()) as has_out", nid=nid).single()
                        if res and not res["has_out"]:
                            nodes[nid]["role"] = "CASHOUT"
                            cash_out_points.append(nid)
                            
                neo4j_online = True
        except Exception:
            pass

        if not neo4j_online:
            # High-fidelity BFS traversal on SQLite
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            queue = [(account_id, 0)]
            visited = {account_id}
            
            try:
                while queue:
                    curr, hop = queue.pop(0)
                    if hop >= max_hops:
                        continue
                        
                    # Fetch all downstream transactions
                    cursor.execute(
                        "SELECT receiver_account, amount, channel, timestamp FROM transactions WHERE sender_account = ?",
                        (curr,)
                    )
                    txs = cursor.fetchall()
                    
                    if not txs and curr != account_id:
                        nodes[curr]["role"] = "CASHOUT"
                        if curr not in cash_out_points:
                            cash_out_points.append(curr)
                        continue

                    for tx in txs:
                        dst = tx["receiver_account"]
                        amt = tx["amount"]
                        
                        # Handle possible COMP-3 cent division
                        if amt > 100000000:
                            amt = amt / 100.0
                            
                        ch = tx["channel"] or "UPI"
                        ts = tx["timestamp"]
                        
                        if curr == account_id:
                            total_amount_traced += amt

                        if dst not in nodes:
                            nodes[dst] = {"id": dst, "role": "RELAY", "amount_received": 0.0, "amount_forwarded": 0.0}
                        
                        nodes[curr]["amount_forwarded"] += amt
                        nodes[dst]["amount_received"] += amt
                        
                        edges.append({
                            "source": curr,
                            "target": dst,
                            "amount": amt,
                            "channel": ch,
                            "timestamp": ts
                        })
                        
                        if dst not in visited:
                            visited.add(dst)
                            queue.append((dst, hop + 1))
            except Exception as e:
                logger.error(f"SQLite trace downstream failed: {e}")
            finally:
                conn.close()

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "cash_out_points": cash_out_points,
            "total_amount_traced": round(total_amount_traced, 2)
        }

    def trace_upstream(self, account_id: str, max_hops: int = 4) -> dict:
        """
        Traces funds backwards to uncover the original scam/source account.
        """
        nodes = {account_id: {"id": account_id, "role": "TARGET", "amount_in": 0.0, "amount_out": 0.0}}
        edges = []
        sources = []
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        queue = [(account_id, 0)]
        visited = {account_id}
        
        try:
            while queue:
                curr, hop = queue.pop(0)
                if hop >= max_hops:
                    continue
                    
                # Fetch incoming transactions
                cursor.execute(
                    "SELECT sender_account, amount, channel, timestamp FROM transactions WHERE receiver_account = ?",
                    (curr,)
                )
                txs = cursor.fetchall()
                
                if not txs and curr != account_id:
                    nodes[curr]["role"] = "SOURCE"
                    if curr not in sources:
                        sources.append(curr)
                    continue

                for tx in txs:
                    src = tx["sender_account"]
                    amt = tx["amount"]
                    if amt > 100000000:
                        amt = amt / 100.0
                        
                    ch = tx["channel"] or "UPI"
                    ts = tx["timestamp"]
                    
                    if src not in nodes:
                        nodes[src] = {"id": src, "role": "INFLOW_RELAY", "amount_in": 0.0, "amount_out": 0.0}
                        
                    nodes[src]["amount_out"] += amt
                    nodes[curr]["amount_in"] += amt
                    
                    edges.append({
                        "source": src,
                        "target": curr,
                        "amount": amt,
                        "channel": ch,
                        "timestamp": ts
                    })
                    
                    if src not in visited:
                        visited.add(src)
                        queue.append((src, hop + 1))
        except Exception as e:
            logger.error(f"SQLite trace upstream failed: {e}")
        finally:
            conn.close()

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "sources": sources
        }

    def generate_flow_summary(self, trace_result: dict) -> str:
        """Generates a human-readable flow summary narrative for STR filing compliance."""
        total = trace_result.get("total_amount_traced", 0.0)
        cash_outs = trace_result.get("cash_out_points", [])
        edges = trace_result.get("edges", [])
        
        if total == 0.0 or not edges:
            return "No transaction flow links found for this account."

        channels = set(e["channel"] for e in edges)
        channels_str = " / ".join(channels)
        
        relays_count = len(trace_result.get("nodes", [])) - len(cash_outs) - 1
        relays_str = f"{relays_count} intermediate relay hops" if relays_count > 0 else "direct paths"

        summary = (
            f"₹{total:,.2f} entered the suspect account and flowed via {channels_str} "
            f"across {relays_str} within a multi-hop layering cycle. "
            f"Final cash-out behavior was detected at {len(cash_outs)} terminal accounts "
        )
        
        if cash_outs:
            summary += f"(including {', '.join(cash_outs[:3])})."
        else:
            summary += "with layering patterns indicative of rapid funds diversion."
            
        return summary
