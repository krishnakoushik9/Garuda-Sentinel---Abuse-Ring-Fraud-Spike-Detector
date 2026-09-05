import os
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from src.config import SEQ_LEN

class VariationalDropout(nn.Module):
    """
    Applies the same dropout mask across all time steps in a sequence.
    This preserves temporal consistency in the dropped-out features.
    """
    def __init__(self, dropout=0.3):
        super().__init__()
        self.dropout = dropout

    def forward(self, x):
        if not self.training or self.dropout == 0:
            return x
        # x shape: (batch, seq_len, features)
        # We sample a mask of shape (batch, 1, features)
        mask = x.new_empty(x.size(0), 1, x.size(2), requires_grad=False).bernoulli_(1 - self.dropout)
        return x * mask / (1 - self.dropout)

class ImprovedLSTMAnomalyDetector(nn.Module):
    """
    State-of-the-art Deep Temporal Autoencoder for transaction sequence anomaly detection.
    Features:
      - Learnable Positional Encoding to capture temporal order.
      - 3-Layer Bidirectional LSTM Encoder to capture both forward and backward behavioral dynamics.
      - 8-Head Multi-Head Attention layer between encoder and decoder.
      - Variational Dropout for robust hidden feature regularization.
      - 3-Layer Decoder LSTM to reconstruct the original sequence.
    """
    def __init__(self, seq_len=None, n_features=5, hidden_dim=256, num_layers=3, dropout=0.3):
        super(ImprovedLSTMAnomalyDetector, self).__init__()
        self.seq_len = seq_len or SEQ_LEN
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # 1. Learnable Positional Encoding
        self.pos_embedding = nn.Parameter(torch.randn(1, self.seq_len, n_features) * 0.02)
        
        # 2. Encoder: 3-Layer Bidirectional LSTM
        self.encoder_lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        # 3. Multi-Head Attention (8 heads)
        # Encoder is bidirectional, so output dim is 2 * hidden_dim
        encoder_out_dim = 2 * hidden_dim
        self.attention = nn.MultiheadAttention(
            embed_dim=encoder_out_dim,
            num_heads=8,
            batch_first=True
        )
        
        # 4. Projection layer to project attention outputs to decoder hidden dimension
        self.attn_projection = nn.Linear(encoder_out_dim, hidden_dim)
        
        # 5. Variational Dropout (dropout=0.3)
        self.var_dropout = VariationalDropout(dropout=dropout)
        
        # 6. Decoder: 3-Layer LSTM
        self.decoder_lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        # 7. Reconstruction Linear Layer
        self.reconstruct_linear = nn.Linear(hidden_dim, n_features)

    def forward(self, x):
        # x shape: (batch, seq_len, n_features)
        
        # Step 1: Add learnable positional encoding
        # Trim or pad pos_embedding if seq_len changes dynamically
        if x.size(1) == self.pos_embedding.size(1):
            pos_emb = self.pos_embedding
        else:
            # Handle dynamic length slice if needed
            pos_emb = self.pos_embedding[:, :x.size(1), :]
            
        x_pos = x + pos_emb
        
        # Step 2: Encoder pass
        # encoder_out shape: (batch, seq_len, 2 * hidden_dim)
        encoder_out, _ = self.encoder_lstm(x_pos)
        
        # Step 3: Multi-head Attention
        # Queries, Keys, and Values all derive from the bidirectional encoder output
        attn_out, _ = self.attention(encoder_out, encoder_out, encoder_out)
        
        # Step 4: Projection to Decoder Dimension (256)
        projected = self.attn_projection(attn_out)
        
        # Step 5: Variational Dropout
        projected = self.var_dropout(projected)
        
        # Step 6: Decoder pass
        decoder_out, _ = self.decoder_lstm(projected)
        
        # Step 7: Linear Reconstruction
        reconstructed = self.reconstruct_linear(decoder_out)
        return reconstructed

    def anomaly_score(self, x):
        self.eval()
        with torch.no_grad():
            reconstructed = self.forward(x)
            # Compute Mean Squared Error (MSE) reconstruction loss
            mse = torch.mean((x - reconstructed)**2, dim=(1, 2)).cpu().numpy()
            
            # Extract raw sequence features for domain-informed anomaly scaling
            # x shape: (batch, seq_len, n_features)
            x_np = x.cpu().numpy()
            num_features = x_np.shape[2]
            
            if num_features >= 12:
                # Use highly discriminative 12-feature composite sequence risk score
                # index 2: fan_out_ratio, 5: txn_velocity_1h, 6: txn_velocity_24h, 7: txn_velocity_7d,
                # 8: unique_beneficiaries_7d, 10: suspicious_neighbor_count, 11: hop_2_mule_count
                max_fan_out = np.max(x_np[:, :, 2], axis=1)
                max_v1h = np.max(x_np[:, :, 5], axis=1)
                max_v24h = np.max(x_np[:, :, 6], axis=1)
                max_v7d = np.max(x_np[:, :, 7], axis=1)
                max_ub7d = np.max(x_np[:, :, 8], axis=1)
                max_neigh = np.max(x_np[:, :, 10], axis=1)
                max_hop2 = np.max(x_np[:, :, 11], axis=1)
                
                sequence_behavior_risk = (
                    max_fan_out + 
                    max_v1h + 
                    max_v24h + 
                    max_v7d + 
                    max_ub7d + 
                    2.0 * max_neigh + 
                    3.0 * max_hop2
                )
            else:
                # Fallback to 5-feature composite sequence risk score
                max_new_ben = np.max(x_np[:, :, 1], axis=1) if num_features > 1 else np.zeros(len(x_np))
                max_fan_out = np.max(x_np[:, :, 2], axis=1) if num_features > 2 else np.zeros(len(x_np))
                max_dormancy = np.max(x_np[:, :, 3], axis=1) if num_features > 3 else np.zeros(len(x_np))
                max_night_txn = np.max(x_np[:, :, 4], axis=1) if num_features > 4 else np.zeros(len(x_np))
                max_amount_abs = np.max(np.abs(x_np[:, :, 0]), axis=1)
                
                sequence_behavior_risk = (
                    max_new_ben + 
                    max_fan_out + 
                    max_dormancy + 
                    max_night_txn + 
                    0.5 * max_amount_abs
                )
            
            # Hybrid score: combines deep temporal reconstruction error with temporal behavior spikes
            hybrid_score = mse + 0.35 * sequence_behavior_risk
            
            # Normalize to [0.0, 1.0] range for standard API consumption
            min_score = hybrid_score.min()
            max_score = hybrid_score.max()
            if max_score > min_score:
                normalized_score = (hybrid_score - min_score) / (max_score - min_score)
            else:
                normalized_score = np.zeros_like(hybrid_score)
                
            return normalized_score



# Backward compatibility alias
TransactionSequenceAutoencoder = ImprovedLSTMAnomalyDetector

def prepare_account_sequence(df, account_id, seq_len=None, features=None):
    """Extract and pad/truncate transaction sequence for an account."""
    if seq_len is None:
        seq_len = SEQ_LEN
    if features is None:
        features = ['amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag', 'night_txn_ratio']
        
    acc_tx = df[df['sender_account'] == account_id].sort_values('timestamp')
    if acc_tx.empty:
        return np.zeros((1, seq_len, len(features)))
    
    # Filter only available columns and pad missing columns with zeros
    n_features = len(features)
    seq_data = np.zeros((len(acc_tx), n_features))
    for idx, col in enumerate(features):
        if col in acc_tx.columns:
            seq_data[:, idx] = acc_tx[col].values
            
    seq_data = seq_data[-seq_len:]
    if len(seq_data) < seq_len:
        padding = np.zeros((seq_len - len(seq_data), n_features))
        seq_data = np.vstack([padding, seq_data])
    
    return seq_data.reshape(1, seq_len, n_features)

if __name__ == "__main__":
    print("--- Improved LSTM Autoencoder Demo ---")
    seq_len = 15
    n_features = 5
    
    model = ImprovedLSTMAnomalyDetector(seq_len=seq_len, n_features=n_features)
    mock_input = torch.randn(8, seq_len, n_features)
    
    output = model(mock_input)
    print("Output Shape (should match [8, 15, 5]):", output.shape)
    
    scores = model.anomaly_score(mock_input)
    print("Anomaly Scores (first 5):", scores[:5])
    
    save_path = Path(__file__).resolve().parents[2] / "models" / "lstm_ae.pt"
    os.makedirs(save_path.parent, exist_ok=True)
    torch.save(model.state_dict(), str(save_path))
    print(f"Model saved to {save_path}")
