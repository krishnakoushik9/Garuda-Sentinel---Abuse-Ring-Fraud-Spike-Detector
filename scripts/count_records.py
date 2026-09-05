import sqlite3
conn = sqlite3.connect("database/ecosystem.db")
print("Accounts:", conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0])
print("Transactions:", conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
print("Mule Accounts:", conn.execute("SELECT COUNT(*) FROM mule_accounts").fetchone()[0])
conn.close()
