import sqlite3
conn = sqlite3.connect("database/ecosystem.db")
print("Unique connections:", conn.execute("SELECT COUNT(DISTINCT sender_account || '-' || receiver_account) FROM transactions").fetchone()[0])
conn.close()
