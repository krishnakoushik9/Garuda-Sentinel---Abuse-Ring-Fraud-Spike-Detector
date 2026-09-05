import pandas as pd
import torch
import numpy as np
from torch_geometric.data import Data
import sqlite3
from src.config import SQLITE_DB_PATH

# 8 standard channels mapping to integers
CHANNEL_MAPPING = {
    "UPI": 0.0,
    "IMPS": 1.0,
    "NEFT": 2.0,
    "RTGS": 3.0,
    "CARD": 4.0,
    "ATM": 5.0,
    "MERCHANT": 6.0,
    "WALLET": 7.0
}

def build_transaction_graph(transactions, db_path=None):
    """
    Convert a list of transaction dicts or pandas DataFrame to PyG Data object.
    Includes node features and edge attributes: amount, channel_encoded, time_since_last.
    Also computes node timestamps for temporal GNN sampling.
    """
    if isinstance(transactions, pd.DataFrame):
        transactions = transactions.to_dict('records')
        
    db_path = db_path or SQLITE_DB_PATH
    
    # 1. Identify all unique accounts (nodes)
    account_ids = set()
    for t in transactions:
        account_ids.add(t['sender_account'])
        account_ids.add(t['receiver_account'])
        
    sorted_accounts = sorted(list(account_ids))
    id_map = {aid: i for i, aid in enumerate(sorted_accounts)}
    num_nodes = len(id_map)
    
    # 2. Get node features (x) - Default to randn or load cached features from DB
    x = torch.randn(num_nodes, 12)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transaction_features'")
        if cursor.fetchone():
            # If the cached transaction features exist, fetch average feature representations for nodes
            for i, aid in enumerate(sorted_accounts):
                row = conn.execute("""
                    SELECT AVG(amount_zscore) as f0, AVG(is_new_beneficiary) as f1, AVG(fan_out_ratio) as f2,
                           AVG(dormancy_break_flag) as f3, AVG(night_txn_ratio) as f4, AVG(txn_velocity_1h) as f5,
                           AVG(txn_velocity_24h) as f6, AVG(txn_velocity_7d) as f7, AVG(unique_beneficiaries_7d) as f8,
                           AVG(graph_degree_centrality) as f9, AVG(suspicious_neighbor_count) as f10, AVG(hop_2_mule_count) as f11
                    FROM transaction_features WHERE account_id = ?
                """, (aid,)).fetchone()
                if row and row['f0'] is not None:
                    x[i] = torch.tensor([
                        row['f0'], row['f1'], row['f2'], row['f3'], row['f4'], row['f5'],
                        row['f6'], row['f7'], row['f8'], row['f9'], row['f10'], row['f11']
                    ], dtype=torch.float32)
        conn.close()
    except Exception:
        # Fall back gracefully to standard normal node initialization
        pass

    # 3. Sort transactions chronologically to compute time_since_last and timestamps
    txns_with_ts = []
    for t in transactions:
        ts_str = t.get('timestamp')
        if not ts_str:
            ts = pd.Timestamp.now()
        else:
            ts = pd.to_datetime(ts_str)
        txns_with_ts.append((t, ts))
        
    txns_with_ts = sorted(txns_with_ts, key=lambda pair: pair[1])
    
    edge_src = []
    edge_dst = []
    edge_attr_list = []
    
    # We will track the last transaction timestamp for each sender to calculate time_since_last
    last_tx_time = {}
    # We will track the latest transaction timestamp for each node (account) to set node timestamps
    node_last_timestamp = {aid: 0.0 for aid in sorted_accounts}
    
    for t, ts in txns_with_ts:
        s = t['sender_account']
        r = t['receiver_account']
        
        s_idx = id_map[s]
        r_idx = id_map[r]
        
        edge_src.append(s_idx)
        edge_dst.append(r_idx)
        
        # 1. amount
        amount = float(t.get('amount', 0.0))
        
        # 2. channel_encoded
        channel = t.get('channel', 'UPI')
        channel_encoded = CHANNEL_MAPPING.get(str(channel).upper(), 0.0)
        
        # 3. time_since_last (in seconds)
        ts_float = ts.timestamp()
        if s in last_tx_time:
            time_since_last = float(ts_float - last_tx_time[s])
        else:
            time_since_last = 0.0
            
        last_tx_time[s] = ts_float
        
        # Update node timestamps
        node_last_timestamp[s] = max(node_last_timestamp[s], ts_float)
        node_last_timestamp[r] = max(node_last_timestamp[r], ts_float)
        
        edge_attr_list.append([amount, channel_encoded, time_since_last])
        
    # Construct PyTorch Tensors
    if not edge_src:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, 3), dtype=torch.float32)
    else:
        edge_index = torch.tensor([edge_src, edge_dst], dtype=torch.long)
        edge_attr = torch.tensor(edge_attr_list, dtype=torch.float32)
        
    # Node timestamps for PyG temporal NeighborLoader
    node_timestamps = torch.tensor([node_last_timestamp[aid] for aid in sorted_accounts], dtype=torch.float32)
    
    data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
    data.timestamp = node_timestamps
    
    return data
