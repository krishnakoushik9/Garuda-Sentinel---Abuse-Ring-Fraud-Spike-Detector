import sqlite3
conn = sqlite3.connect("database/ecosystem.db")
cursor = conn.cursor()

mule_communities = [r[0] for r in cursor.execute("""
    SELECT DISTINCT community_id 
    FROM graph_analytics 
    WHERE account_id IN (SELECT account_id FROM mule_accounts) AND community_id IS NOT NULL AND community_id != ''
""").fetchall()]

print("Number of communities containing at least one mule:", len(mule_communities))

placeholders = ",".join(["?"] * len(mule_communities))
community_accounts = [r[0] for r in cursor.execute(f"""
    SELECT account_id 
    FROM graph_analytics 
    WHERE community_id IN ({placeholders})
""", mule_communities).fetchall()]

print("Number of accounts in these communities:", len(community_accounts))

# Transactions involving community accounts
accounts_placeholders = ",".join(["?"] * len(community_accounts))
txn_count = cursor.execute(f"""
    SELECT COUNT(*) 
    FROM transactions 
    WHERE sender_account IN ({accounts_placeholders}) OR receiver_account IN ({accounts_placeholders})
""", community_accounts + community_accounts).fetchone()[0]

print("Number of transactions involving these community accounts:", txn_count)

conn.close()
