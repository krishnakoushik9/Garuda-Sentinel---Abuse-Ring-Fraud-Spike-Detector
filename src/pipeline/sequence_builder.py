import numpy as np
import pandas as pd
from src.config import SEQ_LEN

class SequenceBuilder:
    """
    Constructs temporal sequence windows of transaction features for the LSTM Autoencoder.
    Supports padding, truncation, and dynamic sequence length tuning.
    """
    def __init__(self, seq_len=None):
        self.seq_len = seq_len or SEQ_LEN

    def build_sequences(self, transactions, feature_matrix, feature_cols=None):
        """
        Groups features by sender account to build 3D sequence tensors.
        
        Args:
            transactions (list): List of transaction dicts sorted chronologically.
            feature_matrix (np.ndarray or list): Parallel feature array matching `transactions`.
            feature_cols (list, optional): Subset of feature indices/columns to use. Default is first 5.
            
        Returns:
            np.ndarray: Sequence tensor of shape (num_senders, seq_len, num_features)
            list: List of corresponding sender account IDs.
        """
        if feature_cols is None:
            # Use first 5 features: amount_zscore, is_new_beneficiary, fan_out_ratio, dormancy_break_flag, night_txn_ratio
            num_features = 5
        else:
            num_features = len(feature_cols)

        # Convert feature matrix to numpy array for efficient indexing
        feats_arr = np.array(feature_matrix)

        # Group transaction feature indices by sender account
        features_by_sender = {}
        for i, tx in enumerate(transactions):
            sender = tx['sender_account']
            if sender not in features_by_sender:
                features_by_sender[sender] = []
            
            # Extract features (optionally filtering columns)
            if feature_cols is None:
                feat_vec = feats_arr[i][:num_features]
            else:
                feat_vec = feats_arr[i][feature_cols]
            features_by_sender[sender].append(feat_vec)

        # Construct padded/truncated sequences for each unique sender
        sequences = []
        senders = list(features_by_sender.keys())

        for sender in senders:
            sender_feats = features_by_sender[sender]
            if not sender_feats:
                seq_data = np.zeros((self.seq_len, num_features))
            else:
                # Take last seq_len features
                seq_data = np.array(sender_feats[-self.seq_len:])
                # Pad if the history is shorter than seq_len
                if len(seq_data) < self.seq_len:
                    padding = np.zeros((self.seq_len - len(seq_data), num_features))
                    seq_data = np.vstack([padding, seq_data])
            sequences.append(seq_data)

        return np.array(sequences), senders

    def prepare_single_sequence(self, df, account_id, feature_cols=None):
        """
        Extracts, pads, or truncates a sequence for a single account from a DataFrame.
        """
        if feature_cols is None:
            feature_cols = ['amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag', 'night_txn_ratio']
            
        acc_tx = df[df['sender_account'] == account_id].sort_values('timestamp')
        n_features = len(feature_cols)
        
        if acc_tx.empty:
            return np.zeros((1, self.seq_len, n_features))
        
        # Check if requested features exist in the DataFrame, otherwise use default mappings
        available_cols = [c for c in feature_cols if c in acc_tx.columns]
        if len(available_cols) < n_features:
            # Fallback to zeros or whatever columns are present, padding up to requested length
            seq_data = np.zeros((len(acc_tx), n_features))
            for idx, col in enumerate(feature_cols):
                if col in acc_tx.columns:
                    seq_data[:, idx] = acc_tx[col].values
        else:
            seq_data = acc_tx[feature_cols].values
            
        seq_data = seq_data[-self.seq_len:]
        if len(seq_data) < self.seq_len:
            padding = np.zeros((self.seq_len - len(seq_data), n_features))
            seq_data = np.vstack([padding, seq_data])
            
        return seq_data.reshape(1, self.seq_len, n_features)
