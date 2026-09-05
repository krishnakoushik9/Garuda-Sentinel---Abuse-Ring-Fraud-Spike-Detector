import sqlite3
from neo4j import GraphDatabase
from src.config import SQLITE_DB_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

class Neo4jLoader:
    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.db_path = SQLITE_DB_PATH
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            self.enabled = True
        except Exception as e:
            print(f"Neo4j connection failed: {e}. Loader running in disabled mode.")
            self.enabled = False

    def close(self):
        if self.enabled:
            self.driver.close()

    def load_accounts(self, batch_size=500):
        """Load accounts in batches from SQLite to Neo4j."""
        if not self.enabled: return
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        total = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        print(f"Starting to load {total} accounts into Neo4j...")
        
        query = """
        UNWIND $rows AS row
        MERGE (a:Account {account_id: row.account_id})
        SET a.name = row.name,
            a.segment = row.customer_segment,
            a.city = row.city,
            a.risk_profile = row.risk_profile
        """
        
        cursor = conn.cursor()
        cursor.execute("SELECT account_id, name, customer_segment, city, risk_profile FROM accounts")
        
        count = 0
        with self.driver.session() as session:
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                
                session.run(query, rows=[dict(r) for r in rows])
                count += len(rows)
                if count % 10000 == 0 or count == total:
                    print(f"Accounts load progress: {count}/{total} records loaded.")
                    
        print(f"Completed loading {count} accounts into Neo4j.")
        conn.close()

    def load_transactions(self, batch_size=500):
        """Load transactions in batches from SQLite to Neo4j as SENT_TO relationships."""
        if not self.enabled: return
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        print(f"Starting to load {total} transactions into Neo4j...")
        
        query = """
        UNWIND $rows AS row
        MATCH (s:Account {account_id: row.sender_account})
        MATCH (r:Account {account_id: row.receiver_account})
        MERGE (s)-[rel:SENT_TO {transaction_id: row.transaction_id}]->(r)
        SET rel.amount = row.amount,
            rel.timestamp = row.timestamp,
            rel.channel = row.channel
        """
        
        cursor = conn.cursor()
        cursor.execute("SELECT transaction_id, sender_account, receiver_account, amount, timestamp, channel FROM transactions")
        
        count = 0
        with self.driver.session() as session:
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                
                dicts = []
                for r in rows:
                    d = dict(r)
                    if isinstance(d.get("amount"), (int, float)) and d.get("amount", 0) > 100000000:
                        d["amount"] = d["amount"] / 100.0
                    dicts.append(d)
                    
                session.run(query, rows=dicts)
                count += len(rows)
                if count % 10000 == 0 or count == total:
                    print(f"Transactions load progress: {count}/{total} records loaded.")
                    
        print(f"Completed loading {count} transactions into Neo4j.")
        conn.close()

if __name__ == "__main__":
    print("--- Neo4jLoader Batched Seeder ---")
    loader = Neo4jLoader()
    try:
        if loader.enabled:
            loader.load_accounts()
            loader.load_transactions()
        else:
            print("Neo4j not reachable. Skipping load.")
    finally:
        loader.close()
