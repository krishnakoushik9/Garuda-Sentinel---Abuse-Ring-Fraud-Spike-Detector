import os
import time
import json
import sqlite3
import pandas as pd
import numpy as np
import statistics
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import redis
from src.config import SQLITE_DB_PATH

@dataclass
class TransactionFeatures:
    transaction_id: str
    account_id: str
    amount: float
    amount_zscore: float
    is_new_beneficiary: float
    fan_out_ratio: float
    dormancy_break_flag: float
    night_txn_ratio: float
    txn_velocity_1h: float
    txn_velocity_24h: float
    txn_velocity_7d: float
    unique_beneficiaries_7d: float
    graph_degree_centrality: float
    suspicious_neighbor_count: float
    hop_2_mule_count: float

    def to_array(self) -> np.ndarray:
        return np.array([
            self.amount_zscore,
            self.is_new_beneficiary,
            self.fan_out_ratio,
            self.dormancy_break_flag,
            self.night_txn_ratio,
            self.txn_velocity_1h,
            self.txn_velocity_24h,
            self.txn_velocity_7d,
            self.unique_beneficiaries_7d,
            self.graph_degree_centrality,
            self.suspicious_neighbor_count,
            self.hop_2_mule_count
        ], dtype=float)

class FeatureEngineer:
    def __init__(self, redis_host='localhost', redis_port=6379, db_path=None):
        self.db_path = db_path or SQLITE_DB_PATH
        try:
            self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            self.redis.ping()
            self.use_redis = True
        except Exception:
            self.use_redis = False
            self.mock_store = {}
            
        # Initialize SQLite features cache
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transaction_features (
                    transaction_id TEXT PRIMARY KEY,
                    account_id TEXT,
                    amount REAL,
                    amount_zscore REAL,
                    is_new_beneficiary REAL,
                    fan_out_ratio REAL,
                    dormancy_break_flag REAL,
                    night_txn_ratio REAL,
                    txn_velocity_1h REAL,
                    txn_velocity_24h REAL,
                    txn_velocity_7d REAL,
                    unique_beneficiaries_7d REAL,
                    graph_degree_centrality REAL,
                    suspicious_neighbor_count REAL,
                    hop_2_mule_count REAL
                )
            """)
            conn.commit()
        except Exception as e:
            print("Failed to initialize feature cache table:", e)
        finally:
            conn.close()

    def _get_key(self, account_id: str, feature: str) -> str:
        return f"acc:{account_id}:{feature}"

    def compute_features(self, *args, **kwargs) -> TransactionFeatures:
        """Compute all features for a single transaction dynamically."""
        # Unpack arguments flexibly
        account_id = None
        transaction = None
        
        if 'account_id' in kwargs and 'transaction' in kwargs:
            account_id = kwargs['account_id']
            transaction = kwargs['transaction']
        elif len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            account_id = args[0]
            transaction = args[1]
        elif len(args) >= 1 and isinstance(args[0], dict):
            transaction = args[0]
            account_id = transaction.get('sender_account')
        elif 'tx' in kwargs:
            transaction = kwargs['tx']
            account_id = transaction.get('sender_account')
        else:
            raise ValueError("Invalid arguments passed to compute_features")
            
        if not account_id:
            account_id = transaction.get('sender_account', 'UNKNOWN')

        amount = float(transaction.get('amount', 0.0))
        receiver_id = transaction.get('receiver_account', '')
        current_time = transaction.get('timestamp')
        if not current_time:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        elif hasattr(current_time, 'strftime'):
            current_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            current_time = str(current_time)

        # Check SQLite feature cache first
        transaction_id = transaction.get('transaction_id')
        if transaction_id and transaction_id != 'UNKNOWN':
            conn_cache = sqlite3.connect(self.db_path)
            conn_cache.row_factory = sqlite3.Row
            cursor_cache = conn_cache.cursor()
            try:
                cached = cursor_cache.execute(
                    "SELECT * FROM transaction_features WHERE transaction_id = ?",
                    (transaction_id,)
                ).fetchone()
                if cached:
                    return TransactionFeatures(
                        transaction_id=cached['transaction_id'],
                        account_id=cached['account_id'],
                        amount=cached['amount'],
                        amount_zscore=cached['amount_zscore'],
                        is_new_beneficiary=cached['is_new_beneficiary'],
                        fan_out_ratio=cached['fan_out_ratio'],
                        dormancy_break_flag=cached['dormancy_break_flag'],
                        night_txn_ratio=cached['night_txn_ratio'],
                        txn_velocity_1h=cached['txn_velocity_1h'],
                        txn_velocity_24h=cached['txn_velocity_24h'],
                        txn_velocity_7d=cached['txn_velocity_7d'],
                        unique_beneficiaries_7d=cached['unique_beneficiaries_7d'],
                        graph_degree_centrality=cached['graph_degree_centrality'],
                        suspicious_neighbor_count=cached['suspicious_neighbor_count'],
                        hop_2_mule_count=cached['hop_2_mule_count']
                    )
            except Exception as e:
                print("Error reading features cache:", e)
            finally:
                conn_cache.close()

        # Connect to SQLite
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. amount_zscore
            cursor.execute(
                "SELECT amount FROM transactions WHERE sender_account = ? ORDER BY timestamp DESC LIMIT 100",
                (account_id,)
            )
            rows = cursor.fetchall()
            amounts = [r['amount'] for r in rows]
            # Handle possible COMP-3 cent division
            amounts = [a / 100.0 if isinstance(a, (int, float)) and a > 100000000 else a for a in amounts]
            
            if len(amounts) > 1:
                mean_amt = sum(amounts) / len(amounts)
                try:
                    std_amt = statistics.stdev(amounts)
                except Exception:
                    std_amt = 1.0
                if std_amt == 0:
                    std_amt = 1.0
                amount_zscore = (amount - mean_amt) / std_amt
            else:
                amount_zscore = 0.05

            # 2. is_new_beneficiary
            cursor.execute(
                "SELECT 1 FROM transactions WHERE sender_account = ? AND receiver_account = ? LIMIT 1",
                (account_id, receiver_id)
            )
            is_new_beneficiary = 0.0 if cursor.fetchone() else 1.0

            # 3. fan_out_ratio ( receivers / senders last 7 days )
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT receiver_account) as unique_receivers,
                    COUNT(DISTINCT sender_account) as unique_senders
                FROM transactions
                WHERE (sender_account = ? OR receiver_account = ?)
                  AND timestamp BETWEEN datetime(?, '-7 days') AND ?
            """, (account_id, account_id, current_time, current_time))
            ratio_row = cursor.fetchone()
            if ratio_row and ratio_row['unique_senders'] and ratio_row['unique_senders'] > 0:
                fan_out_ratio = float(ratio_row['unique_receivers']) / float(ratio_row['unique_senders'])
            else:
                fan_out_ratio = 0.1

            # 4. dormancy_break_flag
            cursor.execute("""
                SELECT timestamp FROM transactions
                WHERE (sender_account = ? OR receiver_account = ?)
                  AND timestamp < ?
                ORDER BY timestamp DESC LIMIT 1
            """, (account_id, account_id, current_time))
            last_tx_row = cursor.fetchone()
            dormancy_break_flag = 0.0
            if last_tx_row:
                try:
                    last_ts = pd.to_datetime(last_tx_row['timestamp'])
                    curr_ts = pd.to_datetime(current_time)
                    days_diff = (curr_ts - last_ts).days
                    if days_diff > 30:
                        dormancy_break_flag = 1.0
                except Exception:
                    pass
            else:
                dormancy_break_flag = 1.0

            # 5. night_txn_ratio
            cursor.execute("""
                SELECT timestamp FROM transactions
                WHERE sender_account = ?
                ORDER BY timestamp DESC LIMIT 100
            """, (account_id,))
            tx_rows = cursor.fetchall()
            if tx_rows:
                night_count = 0
                for r in tx_rows:
                    try:
                        dt = pd.to_datetime(r['timestamp'])
                        if dt.hour < 5 or dt.hour > 23:
                            night_count += 1
                    except Exception:
                        pass
                night_txn_ratio = float(night_count) / len(tx_rows)
            else:
                night_txn_ratio = 0.08

            # 6. Velocities: 1h, 24h, 7d
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN timestamp >= datetime(?, '-1 hour') THEN 1 ELSE 0 END) as v1h,
                    SUM(CASE WHEN timestamp >= datetime(?, '-24 hours') THEN 1 ELSE 0 END) as v24h,
                    SUM(CASE WHEN timestamp >= datetime(?, '-7 days') THEN 1 ELSE 0 END) as v7d
                FROM transactions
                WHERE sender_account = ? AND timestamp <= ?
            """, (current_time, current_time, current_time, account_id, current_time))
            velocity_row = cursor.fetchone()
            txn_velocity_1h = float(velocity_row['v1h'] or 0) + 1.0
            txn_velocity_24h = float(velocity_row['v24h'] or 0) + 1.0
            txn_velocity_7d = float(velocity_row['v7d'] or 0) + 1.0

            # 7. unique_beneficiaries_7d
            cursor.execute("""
                SELECT COUNT(DISTINCT receiver_account) as unique_b7d
                FROM transactions
                WHERE sender_account = ? AND timestamp BETWEEN datetime(?, '-7 days') AND ?
            """, (account_id, current_time, current_time))
            ub_row = cursor.fetchone()
            unique_beneficiaries_7d = float(ub_row['unique_b7d'] or 0)

            # 8. Graph analytics / cache / redis fallbacks
            # Degree centrality
            cursor.execute("SELECT degree_centrality FROM graph_analytics WHERE account_id = ?", (account_id,))
            g_row = cursor.fetchone()
            graph_degree_centrality = float(g_row['degree_centrality']) if g_row and g_row['degree_centrality'] is not None else 0.02
            
            # Suspicious neighbor count (linked accounts in mule networks)
            cursor.execute("SELECT COUNT(*) FROM mule_accounts WHERE linked_account = ?", (account_id,))
            suspicious_neighbor_count = float(cursor.fetchone()[0])
            if suspicious_neighbor_count == 0.0:
                suspicious_neighbor_count = 0.05
                
            # Hop 2 mule count (accounts in the same chain/community)
            cursor.execute("SELECT COUNT(*) FROM mule_accounts WHERE chain_id IN (SELECT chain_id FROM mule_accounts WHERE account_id = ?)", (account_id,))
            hop_2_mule_count = float(cursor.fetchone()[0])
            if hop_2_mule_count == 0.0:
                hop_2_mule_count = 0.15

        finally:
            conn.close()

        features = TransactionFeatures(
            transaction_id=transaction.get('transaction_id', 'UNKNOWN'),
            account_id=account_id,
            amount=amount,
            amount_zscore=amount_zscore,
            is_new_beneficiary=is_new_beneficiary,
            fan_out_ratio=fan_out_ratio,
            dormancy_break_flag=dormancy_break_flag,
            night_txn_ratio=night_txn_ratio,
            txn_velocity_1h=txn_velocity_1h,
            txn_velocity_24h=txn_velocity_24h,
            txn_velocity_7d=txn_velocity_7d,
            unique_beneficiaries_7d=unique_beneficiaries_7d,
            graph_degree_centrality=graph_degree_centrality,
            suspicious_neighbor_count=suspicious_neighbor_count,
            hop_2_mule_count=hop_2_mule_count
        )

        # Write to SQLite feature cache
        if transaction_id and transaction_id != 'UNKNOWN':
            conn_write = sqlite3.connect(self.db_path)
            try:
                conn_write.execute("""
                    INSERT OR IGNORE INTO transaction_features (
                        transaction_id, account_id, amount, amount_zscore, is_new_beneficiary, fan_out_ratio,
                        dormancy_break_flag, night_txn_ratio, txn_velocity_1h, txn_velocity_24h, txn_velocity_7d,
                        unique_beneficiaries_7d, graph_degree_centrality, suspicious_neighbor_count, hop_2_mule_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction_id,
                    features.account_id,
                    features.amount,
                    features.amount_zscore,
                    features.is_new_beneficiary,
                    features.fan_out_ratio,
                    features.dormancy_break_flag,
                    features.night_txn_ratio,
                    features.txn_velocity_1h,
                    features.txn_velocity_24h,
                    features.txn_velocity_7d,
                    features.unique_beneficiaries_7d,
                    features.graph_degree_centrality,
                    features.suspicious_neighbor_count,
                    features.hop_2_mule_count
                ))
                conn_write.commit()
            except Exception as e:
                print("Error writing features cache:", e)
            finally:
                conn_write.close()

        return features
