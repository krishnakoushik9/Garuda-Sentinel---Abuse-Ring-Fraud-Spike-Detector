import os
import sqlite3
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import xgboost as xgb
import shap
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, average_precision_score

from src.config import SQLITE_DB_PATH, SEQ_LEN
from src.pipeline.feature_engineering import FeatureEngineer
from src.pipeline.sequence_builder import SequenceBuilder
from src.ml.models.xgb_model import XGBoostTrainer
from src.models.graph_sage import MuleDetectionGNN, train_gnn, build_transaction_graph
from src.models.lstm_autoencoder import ImprovedLSTMAnomalyDetector, TransactionSequenceAutoencoder


def train_pipeline(train_limit=None, train_device="cpu"):
    print("====================================================")
    print("      Garuda Sentinel Temporal ML Training Pipeline  ")
    print("====================================================")
    
    device = torch.device('cuda' if train_device == 'cuda' and torch.cuda.is_available() else 'cpu')
    print(f"[COMPUTE] Selected execution device: {device}")
    
    print("Loading SQLite data for training from:", SQLITE_DB_PATH)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Ensure standard indexes exist
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_sender_timestamp ON transactions(sender_account, timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_receiver_timestamp ON transactions(receiver_account, timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_sender_receiver ON transactions(sender_account, receiver_account)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mule_account ON mule_accounts(account_id)")
    conn.commit()
    
    total_transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    
    if train_limit:
        print(f"Loading latest {train_limit} transactions (out of {total_transactions} total).")
        tx_rows = conn.execute(
            "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?",
            (train_limit,)
        ).fetchall()
    else:
        print(f"Loading all {total_transactions} transactions.")
        tx_rows = conn.execute("SELECT * FROM transactions ORDER BY timestamp DESC").fetchall()
        
    transactions = [dict(r) for r in tx_rows]
    
    # Load known mules/frauds
    mule_rows = conn.execute("SELECT account_id FROM mule_accounts").fetchall()
    mule_account_ids = {r['account_id'] for r in mule_rows}
    
    fraud_rows = conn.execute("SELECT transaction_id FROM fraud_events").fetchall()
    fraud_transaction_ids = {r['transaction_id'] for r in fraud_rows}
    conn.close()
    
    print(f"Loaded {len(transactions)} transactions.")
    print(f"Known mule accounts: {len(mule_account_ids)}")
    print(f"Known fraud events: {len(fraud_transaction_ids)}")
    
    # CRITICAL: Sort by transaction_timestamp before splitting (oldest first for time-series)
    print("[TEMPORAL] Sorting transactions chronologically by transaction_timestamp...")
    transactions = sorted(transactions, key=lambda x: pd.to_datetime(x['timestamp']))
    
    # Feature Engineering and Labeling
    fe = FeatureEngineer()
    X = []
    y = []
    
    print("[PIPELINE] Computing feature vectors for XGBoost...")
    for idx, tx in enumerate(transactions):
        feats = fe.compute_features(tx['sender_account'], tx)
        X.append(feats.to_array())
        
        # Label 1 if sender/receiver is mule/fraud, or transaction is explicitly flagged
        is_fraud = 0.0
        if (tx['sender_account'] in mule_account_ids or 
            tx['receiver_account'] in mule_account_ids or 
            tx['transaction_id'] in fraud_transaction_ids):
            is_fraud = 1.0
        y.append(is_fraud)
        
        if (idx + 1) % 2000 == 0:
            print(f"  Processed {idx + 1}/{len(transactions)} feature vectors.")
            
    columns = [
        'amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag',
        'night_txn_ratio', 'txn_velocity_1h', 'txn_velocity_24h', 'txn_velocity_7d',
        'unique_beneficiaries_7d', 'graph_degree_centrality', 'suspicious_neighbor_count', 'hop_2_mule_count'
    ]
    X_df = pd.DataFrame(X, columns=columns)
    y_arr = np.array(y)
    
    # Heuristic labels fallback if no actual labels are in the dataset
    if sum(y_arr) == 0:
        print("[PIPELINE] Warning: No active fraud labels found in sample. Applying heuristic fallback labeling.")
        for i, tx in enumerate(transactions):
            feats = X[i]
            if feats[2] > 0.8 or feats[0] > 3.0 or (feats[3] > 0.5 and tx['amount'] > 50000):
                y_arr[i] = 1.0
                
    if sum(y_arr) == 0:
        y_arr[0] = 1.0
        y_arr[1] = 1.0
        
    print(f"[PIPELINE] Total positive fraud class instances: {int(sum(y_arr))}/{len(y_arr)}")
    
    # Time-series cross-validation configuration
    n_splits = 5
    timestamps = pd.to_datetime([tx['timestamp'] for tx in transactions])
    total_days = (timestamps.max() - timestamps.min()).days
    
    if total_days > 0:
        avg_daily_txns = len(timestamps) / total_days
        # Define test_size as average count of transactions in a 7 days window
        test_size_samples = int(avg_daily_txns * 7)
    else:
        test_size_samples = len(timestamps) // (n_splits + 1)
        
    # Ensure test_size is within bounds
    test_size_samples = max(20, min(test_size_samples, len(transactions) // (n_splits + 1)))
    print(f"[TEMPORAL] Initializing TimeSeriesSplit (n_splits={n_splits}, test_size={test_size_samples} samples ~ 7 days)")
    
    tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size_samples)
    
    # Train/Validation Loop
    fold = 1
    fold_aucroc_scores = []
    fold_aucpr_scores = []
    
    for train_idx, val_idx in tscv.split(X_df):
        X_tr, X_val = X_df.iloc[train_idx], X_df.iloc[val_idx]
        y_tr, y_val = y_arr[train_idx], y_arr[val_idx]
        
        # Ensure classes exist in the validation fold before computing metrics
        if len(np.unique(y_tr)) < 2 or len(np.unique(y_val)) < 2:
            print(f"  Fold {fold}: Skipping due to single-class label distribution in validation set.")
            fold += 1
            continue
            
        # Calculate scale weight for current fold
        scale_weight = (len(y_tr) - sum(y_tr)) / max(1.0, sum(y_tr))
        
        fold_model = xgb.XGBClassifier(
            scale_pos_weight=scale_weight,
            tree_method='hist',
            device=train_device,
            eval_metric='aucpr',
            use_label_encoder=False,
            n_estimators=30,
            random_state=42
        )
        fold_model.fit(X_tr, y_tr)
        
        y_prob = fold_model.predict_proba(X_val)[:, 1]
        auc_roc = roc_auc_score(y_val, y_prob)
        auc_pr = average_precision_score(y_val, y_prob)
        
        fold_aucroc_scores.append(auc_roc)
        fold_aucpr_scores.append(auc_pr)
        
        print(f"  [FOLD {fold}/{n_splits}] Validation ROC-AUC: {auc_roc:.4f} | AUC-PR: {auc_pr:.4f}")
        fold += 1
        
    if fold_aucroc_scores:
        print(f"[TEMPORAL] CV Mean ROC-AUC: {np.mean(fold_aucroc_scores):.4f} | CV Mean AUC-PR: {np.mean(fold_aucpr_scores):.4f}")
    else:
        print("[TEMPORAL] TimeSeriesSplit evaluation completed (no printable metric folds).")
        
    # Phase 1: Train & Calibrate XGBoost model
    print("\n=== Phase 1: Training & Calibrating XGBoost Fraud Scorer ===")
    scale_weight = (len(y_arr) - sum(y_arr)) / max(1.0, sum(y_arr))
    
    trainer = XGBoostTrainer()
    trainer.train(X_df, y_arr, scale_pos_weight=scale_weight, device=train_device)
    trainer.calibrate(X_df, y_arr)
    
    # Phase 2: Train Temporal GNN Mule Detector
    print("\n=== Phase 2: Training Temporal GNN Mule Detector ===")
    try:
        from src.ml.train_gnn import train_temporal_gnn
        train_temporal_gnn(epochs=20, device=train_device)
    except Exception as e:
        print(f"[GNN] Temporal GNN training skipped or failed: {e}")
        
    # Phase 3: Train Improved LSTM Autoencoder (Attention + Bidirectional)
    print("\n=== Phase 3: Training Improved LSTM Autoencoder ===")
    try:
        # Get all unique senders from transactions
        all_senders = list({t['sender_account'] for t in transactions})
        mule_senders = [s for s in all_senders if s in mule_account_ids]
        normal_senders = [s for s in all_senders if s not in mule_account_ids]
        
        print(f"[LSTM] Found {len(mule_senders)} unique mule senders and {len(normal_senders)} unique normal senders.")
        
        # Unsupervised/Semi-supervised anomaly detection paradigm:
        # 1. Train ONLY on normal sequences (e.g. 400 normal accounts)
        # 2. Validate on a mixed set (e.g. 50 normal accounts + 50 mule accounts)
        n_train_normal = min(400, len(normal_senders) - 50)
        n_val_normal = 50
        n_val_mules = min(50, len(mule_senders))
        
        train_selected_senders = normal_senders[:n_train_normal]
        val_normal_senders = normal_senders[n_train_normal : n_train_normal + n_val_normal]
        val_mule_senders = mule_senders[:n_val_mules]
        
        val_selected_senders = val_normal_senders + val_mule_senders
        
        # Standardize features before building sequences to ensure all features have equal scale
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(np.array(X))
        
        # Build sequences using SequenceBuilder with configured SEQ_LEN
        sb = SequenceBuilder(seq_len=SEQ_LEN)
        sequences, senders = sb.build_sequences(transactions, X_scaled, feature_cols=list(range(12)))
        
        # Align sequences with selected training and validation senders
        sender_to_seq = {s: seq for s, seq in zip(senders, sequences)}
        
        train_seqs = []
        for s in train_selected_senders:
            if s in sender_to_seq:
                train_seqs.append(sender_to_seq[s])
        train_seqs = np.array(train_seqs)
        train_labels = np.zeros(len(train_seqs))
        
        val_seqs = []
        val_labels = []
        for s in val_normal_senders:
            if s in sender_to_seq:
                val_seqs.append(sender_to_seq[s])
                val_labels.append(0.0)
        for s in val_mule_senders:
            if s in sender_to_seq:
                val_seqs.append(sender_to_seq[s])
                val_labels.append(1.0)
                
        val_seqs = np.array(val_seqs)
        val_labels = np.array(val_labels)
        
        print(f"[LSTM] Training dataset (Normal only): {len(train_seqs)} samples.")
        print(f"[LSTM] Validation dataset (Mixed): {len(val_seqs)} samples (Normal: {len(val_normal_senders)}, Mule: {len(val_mule_senders)}).")
        
        # Convert to Tensors
        train_tensor = torch.tensor(train_seqs, dtype=torch.float32).to(device)
        val_tensor = torch.tensor(val_seqs, dtype=torch.float32).to(device)
        
        # Instantiate redesigned Improved LSTM Autoencoder with n_features=12
        ae_model = ImprovedLSTMAnomalyDetector(seq_len=SEQ_LEN, n_features=12, hidden_dim=256, num_layers=3, dropout=0.3).to(device)

        
        optimizer = torch.optim.AdamW(ae_model.parameters(), lr=0.003, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3, min_lr=1e-5)
        criterion = nn.MSELoss()
        
        best_val_loss = float('inf')
        best_model_state = None
        best_auc = 0.0
        best_epoch = 0
        
        epochs = 25
        print(f"[LSTM] Commencing training of Improved LSTM Autoencoder for {epochs} epochs...")
        for epoch in range(1, epochs + 1):
            ae_model.train()
            optimizer.zero_grad()
            output = ae_model(train_tensor)
            loss = criterion(output, train_tensor)
            loss.backward()
            
            # Gradient clipping for RNN stability
            torch.nn.utils.clip_grad_norm_(ae_model.parameters(), max_norm=1.0)
            optimizer.step()
            
            # Evaluate on validation split
            ae_model.eval()
            with torch.no_grad():
                # We calculate validation loss on normal validation sequences (since it's an autoencoder)
                val_normal_tensor = val_tensor[val_labels == 0.0]
                val_output = ae_model(val_normal_tensor)
                val_loss = criterion(val_output, val_normal_tensor).item()
                
                # Compute ROC-AUC score using reconstruction MSE error as anomaly scores
                val_scores = ae_model.anomaly_score(val_tensor)
                
                if len(np.unique(val_labels)) > 1:
                    val_auc = roc_auc_score(val_labels, val_scores)
                else:
                    val_auc = 0.5
                    
            scheduler.step(val_loss)
            
            # Checkpoint the best model based on validation reconstruction error
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_state = ae_model.state_dict().copy()
                best_auc = val_auc
                best_epoch = epoch
                
            if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
                print(f"  Epoch {epoch:02d}/{epochs:02d} | Train MSE: {loss.item():.5f} | Val MSE (Normal): {val_loss:.5f} | Val ROC-AUC: {val_auc:.4f} | LR: {optimizer.param_groups[0]['lr']:.6f}")
                
        # Load the best model weights
        if best_model_state is not None:
            ae_model.load_state_dict(best_model_state)
            print(f"[LSTM] Successfully restored best model from Epoch {best_epoch} (Val MSE: {best_val_loss:.5f}, Val ROC-AUC: {best_auc:.4f})")
            
        ae_path = "models/lstm_ae.pt"
        os.makedirs(os.path.dirname(ae_path), exist_ok=True)
        torch.save(ae_model.state_dict(), ae_path)
        print(f"[LSTM] Autoencoder successfully saved to {ae_path}")
        
    except Exception as e:
        print(f"[LSTM] Autoencoder training skipped or failed: {e}")

        
    print("\n[SUCCESS] Pipeline training completed successfully!")

if __name__ == "__main__":
    train_pipeline()
