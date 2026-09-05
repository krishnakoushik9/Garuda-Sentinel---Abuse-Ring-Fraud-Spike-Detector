import sqlite3
import pandas as pd
import os
from pathlib import Path
from src.config import SQLITE_DB_PATH

class CobolBridge:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or SQLITE_DB_PATH

    def get_connection(self):
        """Establish a connection to the SQLite database."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_transactions(self, limit: int = 10000) -> pd.DataFrame:
        """Fetch transactions and return as a pandas DataFrame."""
        query = "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?"
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(limit,))
        
        # Strip potential trailing spaces from TEXT fields
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols:
            df[col] = df[col].astype(str).str.strip()
            
        # Divide amount by 100 if stored as integer cents
        if 'amount' in df.columns:
            df['amount'] = df['amount'].apply(lambda x: x / 100.0 if isinstance(x, (int, float)) and x > 100000000 else x)
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def fetch_accounts(self) -> pd.DataFrame:
        """Fetch account details for feature enrichment."""
        query = "SELECT * FROM accounts"
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols:
            df[col] = df[col].astype(str).str.strip()
            
        return df

    def get_transactions(self, limit: int = 20, offset: int = 0, filters: dict = None) -> list[dict]:
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        if filters:
            if "sender_account" in filters:
                query += " AND sender_account = ?"
                params.append(filters["sender_account"])
            if "receiver_account" in filters:
                query += " AND receiver_account = ?"
                params.append(filters["receiver_account"])
            if "status" in filters:
                query += " AND status = ?"
                params.append(filters["status"])
            if "min_amount" in filters:
                query += " AND amount >= ?"
                params.append(float(filters["min_amount"]))
            if "max_amount" in filters:
                query += " AND amount <= ?"
                params.append(float(filters["max_amount"]))
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("amount"), (int, float)) and d.get("amount", 0) > 100000000:
                    d["amount"] = d["amount"] / 100.0
                results.append(d)
            return results

    def get_account_transactions(self, account_id: str, n: int = 30) -> list[dict]:
        query = "SELECT * FROM transactions WHERE sender_account = ? OR receiver_account = ? ORDER BY timestamp DESC LIMIT ?"
        with self.get_connection() as conn:
            rows = conn.execute(query, (account_id, account_id, n)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("amount"), (int, float)) and d.get("amount", 0) > 100000000:
                    d["amount"] = d["amount"] / 100.0
                results.append(d)
            return results

    def get_account_stats(self, account_id: str) -> dict:
        with self.get_connection() as conn:
            acc_row = conn.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,)).fetchone()
            if not acc_row:
                return {}
            
            acc = dict(acc_row)
            txns = conn.execute(
                "SELECT amount, sender_account, receiver_account FROM transactions WHERE sender_account = ? OR receiver_account = ?",
                (account_id, account_id)
            ).fetchall()
            
            total_sent = 0.0
            total_recv = 0.0
            sent_count = 0
            recv_count = 0
            amounts = []
            
            for t in txns:
                amt = t["amount"]
                if isinstance(amt, (int, float)) and amt > 100000000:
                    amt = amt / 100.0
                amounts.append(amt)
                if t["sender_account"] == account_id:
                    total_sent += amt
                    sent_count += 1
                else:
                    total_recv += amt
                    recv_count += 1
                    
            return {
                "account_id": account_id,
                "name": acc.get("name"),
                "customer_segment": acc.get("customer_segment"),
                "city": acc.get("city"),
                "risk_profile": acc.get("risk_profile"),
                "balance": acc.get("balance"),
                "total_transactions": len(txns),
                "total_sent": total_sent,
                "total_received": total_recv,
                "avg_transaction_amount": sum(amounts) / len(amounts) if amounts else 0.0,
                "max_transaction_amount": max(amounts) if amounts else 0.0,
                "sent_count": sent_count,
                "received_count": recv_count
            }

# Module-level exports
_bridge = CobolBridge()

def get_transactions(limit: int = 20, offset: int = 0, filters: dict = None) -> list[dict]:
    return _bridge.get_transactions(limit=limit, offset=offset, filters=filters)

def get_account_transactions(account_id: str, n: int = 30) -> list[dict]:
    return _bridge.get_account_transactions(account_id=account_id, n=n)

def get_account_stats(account_id: str) -> dict:
    return _bridge.get_account_stats(account_id=account_id)
