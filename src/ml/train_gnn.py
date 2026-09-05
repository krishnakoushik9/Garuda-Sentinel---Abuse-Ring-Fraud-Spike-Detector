import os
import torch
import torch.nn as nn
import sqlite3
import pandas as pd
from torch_geometric.loader import NeighborLoader
from src.config import SQLITE_DB_PATH
from src.pipeline.graph_builder import build_transaction_graph
from src.ml.models.gnn_model import MuleDetectionGNN

def train_temporal_gnn(epochs=20, device='cpu'):
    """
    Train a Temporal GNN on transaction data using PyTorch Geometric's NeighborLoader.
    Enforces temporal sampling constraints via `time_attr='timestamp'`.
    """
    print("\n====================================================")
    print("      Garuda Sentinel Temporal GNN Training Loop     ")
    print("====================================================")
    
    device = torch.device('cuda' if device == 'cuda' and torch.cuda.is_available() else 'cpu')
    print(f"[GNN COMPUTE] Selected execution device: {device}")
    
    # 1. Load active ledger transactions
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    tx_rows = conn.execute("SELECT * FROM transactions ORDER BY timestamp ASC").fetchall()
    transactions = [dict(r) for r in tx_rows]
    
    # Load known ground-truth mule accounts for supervised penalties
    mule_rows = conn.execute("SELECT account_id FROM mule_accounts").fetchall()
    mule_account_ids = {r['account_id'] for r in mule_rows}
    conn.close()
    
    print(f"[GNN DATA] Loaded {len(transactions)} transactions.")
    print(f"[GNN DATA] Known mule accounts to match: {len(mule_account_ids)}")
    
    if not transactions:
        print("[GNN ERROR] No transaction history found. GNN training aborted.")
        return None
        
    # 2. Compile dynamic graph featuring node averages and custom edge attributes
    print("[GNN GRAPH] Building dynamic transaction graph with edge attributes...")
    data = build_transaction_graph(transactions)
    
    # Align labels with node IDs
    account_ids = sorted(list({t['sender_account'] for t in transactions} | {t['receiver_account'] for t in transactions}))
    labels = torch.zeros(len(account_ids), dtype=torch.long)
    for aid, idx in id_map_from_list(account_ids).items():
        if aid in mule_account_ids:
            labels[idx] = 1
            
    data.y = labels
    
    # 3. Configure the Temporal NeighborLoader
    # Neighbors per hop: 15 for 1st hop, 10 for 2nd hop. Batch size: 2048.
    print("[GNN SAMPLING] Initializing PyG NeighborLoader with temporal sampling (time_attr='timestamp')...")
    loader = NeighborLoader(
        data,
        num_neighbors=[15, 10],
        batch_size=2048,
        time_attr='timestamp',
        input_nodes=None, # Samples all nodes in the graph
        shuffle=True
    )
    
    # 4. Initialize our upgraded MuleDetectionGNN (Transformer Conv + time-encoded)
    model = MuleDetectionGNN(in_channels=12, hidden_channels=64, out_channels=2).to(device)
    
    # Penalize mule class (weight 50.0) due to extreme class imbalance
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    weights = torch.tensor([1.0, 50.0], device=device)
    criterion = nn.NLLLoss(weight=weights)
    
    model.train()
    print(f"[GNN TRAIN] Running {epochs} epochs of temporal batch training...")
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        batches = 0
        for batch in loader:
            optimizer.zero_grad()
            batch = batch.to(device)
            
            # Map batch.timestamp for edge_timestamps if available
            edge_timestamps = None
            if hasattr(batch, 'timestamp') and batch.timestamp is not None:
                if batch.timestamp.size(0) == batch.edge_index.size(1):
                    edge_timestamps = batch.timestamp
                elif batch.timestamp.size(0) == batch.x.size(0):
                    src, dst = batch.edge_index[0], batch.edge_index[1]
                    edge_timestamps = (batch.timestamp[src] + batch.timestamp[dst]) / 2.0
            
            # Run forward pass on batch
            out = model(batch.x, batch.edge_index, edge_attr=batch.edge_attr, edge_timestamps=edge_timestamps)
            
            # Calculate loss only on the target batch nodes (first batch_size nodes) to prevent train leakage
            target_out = out[:batch.batch_size]
            target_y = batch.y[:batch.batch_size]
            
            loss = criterion(target_out, target_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            batches += 1
            
        avg_loss = total_loss / max(1, batches)
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:02d}/{epochs:02d} | Avg Loader Loss: {avg_loss:.4f}")
        
    # Save model state dictionary
    os.makedirs("models", exist_ok=True)
    gnn_path = "models/gnn_mule.pt"
    torch.save(model.state_dict(), gnn_path)
    print(f"[GNN SUCCESS] Temporal GNN model successfully trained & saved to {gnn_path}!")
    
    return model

def id_map_from_list(lst):
    return {item: i for i, item in enumerate(lst)}

if __name__ == "__main__":
    train_temporal_gnn()
