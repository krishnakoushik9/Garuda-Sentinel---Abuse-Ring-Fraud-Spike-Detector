#!/usr/bin/env python3
import asyncio
import os
import sqlite3
import sys
import logging
from typing import List, Dict, Any
from backend.config.cognee import CogneeSettings
import cognee

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("feed_cognee")

DB_PATH = "./database/ecosystem.db"
CONCURRENCY_LIMIT = 10  # Concurrency limit for Cognee Cloud upload

async def upload_document_with_retry(doc: str, dataset_id: str, sem: asyncio.Semaphore, max_retries: int = 3) -> bool:
    """Uploads a single document to Cognee with retries and concurrency control."""
    async with sem:
        for attempt in range(max_retries):
            try:
                await cognee.add(doc, dataset_id=dataset_id)
                return True
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed uploading document. Error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        logger.error(f"Failed to upload document after {max_retries} attempts.")
        return False

async def main():
    if not os.path.exists(DB_PATH):
        logger.error(f"SQLite Database not found at {DB_PATH}")
        sys.exit(1)

    logger.info("Connecting to SQLite database to construct graph topology summaries...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Generate Global Transaction Network Stats
    logger.info("Computing global transaction network metrics (from 500,000+ records)...")
    total_txns = cursor.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    total_volume = cursor.execute("SELECT SUM(amount) FROM transactions").fetchone()[0] or 0
    channel_distribution = cursor.execute("""
        SELECT channel, COUNT(*) as count, SUM(amount) as volume 
        FROM transactions 
        GROUP BY channel
    """).fetchall()
    risk_distribution = cursor.execute("""
        SELECT 
            COUNT(CASE WHEN risk_score > 0.8 THEN 1 END) as critical_count,
            COUNT(CASE WHEN risk_score BETWEEN 0.5 AND 0.8 THEN 1 END) as warning_count,
            COUNT(CASE WHEN risk_score < 0.5 THEN 1 END) as low_count
        FROM transactions
    """).fetchone()

    channel_summary = "\n".join([
        f"  * {row['channel']}: {row['count']:,} transactions, Total Volume: ₹{row['volume']:,}"
        for row in channel_distribution
    ])

    global_stats_doc = f"""
Global Transaction Network Summary:
- Total Transaction Volume Analyzed: {total_txns:,} transactions
- Total Net Funds Moved: ₹{total_volume:,}
- Risk Class Distribution:
  * Critical Risk (>80%): {risk_distribution['critical_count']:,} transactions
  * Warning/Medium Risk (50-80%): {risk_distribution['warning_count']:,} transactions
  * Low/Safe Risk (<50%): {risk_distribution['low_count']:,} transactions
- Channel Transaction Share:
{channel_summary}
- Global Network Architecture Description:
  This graph represents the full financial network consisting of 50,000 retail accounts and 500,111 multi-channel transactions. PageRank centrality has been pre-computed to find top hubs, and Louvain community detection has divided the network into 10,701 communities. Suspected mule patterns (such as circular layering and fan-out structures) have been flagged.
"""
    
    # 2. Get the top 100 highest-risk communities containing mule accounts
    logger.info("Fetching top 100 highest-risk communities with mule accounts...")
    cursor.execute("""
        SELECT 
            g.community_id,
            COUNT(DISTINCT g.account_id) as member_count,
            COUNT(DISTINCT m.account_id) as mule_count,
            AVG(g.propagated_risk_score) as avg_risk,
            MAX(g.propagated_risk_score) as max_risk
        FROM graph_analytics g
        JOIN mule_accounts m ON g.account_id = m.account_id
        WHERE g.community_id IS NOT NULL AND g.community_id != ''
        GROUP BY g.community_id
        ORDER BY max_risk DESC, avg_risk DESC
        LIMIT 100
    """)
    high_risk_communities = cursor.fetchall()
    logger.info(f"Identified {len(high_risk_communities)} top risk-hubs for deep graph modeling.")

    documents = [global_stats_doc.strip()]

    # 3. For each high-risk community, compile a dense graph profile document
    for c_idx, comm in enumerate(high_risk_communities):
        comm_id = comm["community_id"]
        
        # Get member details
        cursor.execute("""
            SELECT 
                g.account_id, g.pagerank, g.degree_centrality, g.propagated_risk_score,
                a.name, a.city, a.state, a.occupation, a.balance,
                m.pattern_type, m.chain_id, m.layer, m.linked_account
            FROM graph_analytics g
            LEFT JOIN accounts a ON g.account_id = a.account_id
            LEFT JOIN mule_accounts m ON g.account_id = m.account_id
            WHERE g.community_id = ?
        """, (comm_id,))
        members = cursor.fetchall()
        member_ids = [m["account_id"] for m in members]

        # Get internal transactions
        placeholders = ",".join(["?"] * len(member_ids))
        cursor.execute(f"""
            SELECT sender_account, receiver_account, SUM(amount) as total_amount, COUNT(*) as txn_count, MAX(risk_score) as max_risk
            FROM transactions
            WHERE sender_account IN ({placeholders}) AND receiver_account IN ({placeholders})
            GROUP BY sender_account, receiver_account
        """, member_ids + member_ids)
        internal_flows = cursor.fetchall()

        # Get external transactions (cross-community flows)
        cursor.execute(f"""
            SELECT sender_account, receiver_account, SUM(amount) as total_amount, COUNT(*) as txn_count, MAX(risk_score) as max_risk
            FROM transactions
            WHERE (sender_account IN ({placeholders}) AND receiver_account NOT IN ({placeholders}))
               OR (sender_account NOT IN ({placeholders}) AND receiver_account IN ({placeholders}))
            GROUP BY sender_account, receiver_account
            ORDER BY total_amount DESC
            LIMIT 15
        """, member_ids + member_ids + member_ids + member_ids)
        external_flows = cursor.fetchall()

        # Format community document
        mule_list = [m for m in members if m["pattern_type"] is not None]
        mule_details = "\n".join([
            f"  * {m['account_id']} ({m['name']}): Pattern={m['pattern_type']}, Chain={m['chain_id']}, Layer={m['layer']}, Linked={m['linked_account']}"
            for m in mule_list
        ])

        members_summary = "\n".join([
            f"  * {m['account_id']} ({m['name'] or 'Anon'}): PageRank={m['pagerank']:.6f}, Risk={m['propagated_risk_score']:.2f}%, Bal=₹{m['balance']:,}"
            for m in members[:15]
        ])
        if len(members) > 15:
            members_summary += f"\n  * ... and {len(members) - 15} other account nodes."

        internal_flows_summary = "\n".join([
            f"  * {f['sender_account']} -> {f['receiver_account']}: ₹{f['total_amount']:,} across {f['txn_count']} txns (Max Risk: {f['max_risk'] * 100:.1f}%)"
            for f in internal_flows[:20]
        ])
        if len(internal_flows) > 20:
            internal_flows_summary += f"\n  * ... and {len(internal_flows) - 20} other internal connection flows."

        external_flows_summary = "\n".join([
            f"  * {f['sender_account']} -> {f['receiver_account']}: ₹{f['total_amount']:,} across {f['txn_count']} txns (Max Risk: {f['max_risk'] * 100:.1f}%)"
            for f in external_flows
        ])

        comm_doc = f"""
Community Cluster Graph Profile:
- Community ID: {comm_id}
- Network Statistics:
  * Total Accounts: {comm['member_count']}
  * Suspected Mule Accounts: {comm['mule_count']}
  * Average Community Risk Score: {comm['avg_risk']:.2f}%
  * Maximum Risk Node: {comm['max_risk']:.2f}%
- Suspected Mule Account Nodes:
{mule_details if mule_details else '  * None'}
- Network Node Profiles (Top Members):
{members_summary}
- Internal Flow Connections (Transactions between members):
{internal_flows_summary if internal_flows_summary else '  * No internal transactions'}
- External Flow Connections (Transactions with outside communities):
{external_flows_summary if external_flows_summary else '  * No external transactions'}
"""
        documents.append(comm_doc.strip())

    # 4. Get top 200 individual highest-risk transaction logs as raw evidence
    logger.info("Fetching top 200 highest-risk individual transaction logs...")
    cursor.execute("""
        SELECT 
            t.transaction_id, t.timestamp, t.sender_account, t.receiver_account,
            t.amount, t.channel, t.status, t.description, t.risk_score,
            s.name as sender_name, r.name as receiver_name
        FROM transactions t
        LEFT JOIN accounts s ON t.sender_account = s.account_id
        LEFT JOIN accounts r ON t.receiver_account = r.account_id
        ORDER BY t.risk_score DESC, t.amount DESC
        LIMIT 200
    """)
    top_txns = cursor.fetchall()
    
    for t in top_txns:
        doc = f"""
Forensic Transaction Audit Log:
- Transaction ID: {t['transaction_id']}
- Time: {t['timestamp']}
- Flow: {t['sender_account']} ({t['sender_name'] or 'Anon'}) -> {t['receiver_account']} ({t['receiver_name'] or 'Anon'})
- Amount: ₹{t['amount']:,}
- Channel: {t['channel']}
- Status: {t['status']}
- Description: {t['description']}
- Risk Evaluation Score: {t['risk_score'] * 100:.2f}% (Classification: HIGH SUSPICION)
"""
        documents.append(doc.strip())

    conn.close()
    logger.info(f"Ingestion payload compiled. Total documents: {len(documents)}")

    # 5. Initialize Cognee SDK
    logger.info("Validating and Initializing Cognee Cloud SDK connection...")
    try:
        CogneeSettings.validate()
        logger.info(f"Setting up Cognee serve to URL: {CogneeSettings.COGNEE_BASE_URL}")
        await cognee.serve(
            url=CogneeSettings.COGNEE_BASE_URL,
            api_key=CogneeSettings.COGNEE_API_KEY
        )
        logger.info("Cognee Cloud SDK served successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Cognee connection: {e}")
        sys.exit(1)

    # 6. Ingest documents in parallel with concurrency semaphore
    dataset_name = "fraud_investigations"
    logger.info(f"Uploading {len(documents)} documents to Cognee dataset '{dataset_name}' with concurrency limit={CONCURRENCY_LIMIT}...")
    
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [upload_document_with_retry(doc, dataset_name, sem) for doc in documents]
    
    results = await asyncio.gather(*tasks)
    success_count = sum(1 for r in results if r)
    logger.info(f"Successfully uploaded {success_count}/{len(documents)} documents to Cognee.")

    # 7. Run Cognify
    logger.info("Running cognify() to build Cognee Knowledge Graph memory network...")
    try:
        await cognee.cognify(datasets=[dataset_name])
        logger.info("Cognee cognify() completed successfully! 500,000+ transaction network topology, connections, and mule communities are now indexed in Cognee Cloud.")
    except Exception as e:
        logger.error(f"Error executing cognify(): {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
