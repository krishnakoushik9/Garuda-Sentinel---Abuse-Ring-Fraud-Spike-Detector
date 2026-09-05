import sqlite3
conn = sqlite3.connect("database/ecosystem.db")
cursor = conn.cursor()
total_communities = cursor.execute("SELECT COUNT(DISTINCT community_id) FROM graph_analytics WHERE community_id IS NOT NULL AND community_id != ''").fetchone()[0]
print("Total communities:", total_communities)
conn.close()
