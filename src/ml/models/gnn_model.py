import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import TransformerConv

class TimeEncoder(nn.Module):
    """
    TimeEncoder maps timestamps or time differences to a 64-dimensional dense vector
    using learnable periodic frequency projections.
    """
    def __init__(self, out_channels=64):
        super(TimeEncoder, self).__init__()
        self.out_channels = out_channels
        # Learnable frequency weights and biases
        self.w = nn.Parameter(torch.randn(1, out_channels))
        self.b = nn.Parameter(torch.randn(1, out_channels))

    def forward(self, t):
        # t can be a 1D tensor [E] or 2D tensor [E, 1]
        if t.ndim == 1:
            t = t.unsqueeze(-1)
        # Periodic sine mapping
        return torch.sin(t * self.w + self.b)

class MuleDetectionGNN(nn.Module):
    """
    Temporal GNN replacing standard static GraphSAGE with an Edge-conditioned
    and Time-encoded Transformer Conv network.
    """
    def __init__(self, in_channels=12, hidden_channels=64, out_channels=2, edge_dim=3, time_dim=64):
        super(MuleDetectionGNN, self).__init__()
        self.time_encoder = TimeEncoder(out_channels=time_dim)
        
        # Dense projection for raw edge features: amount, channel, velocity
        self.edge_proj = nn.Linear(edge_dim, time_dim)
        
        # Transformer Conv layers with integrated edge feature dimensions
        # heads=2 with concat=True yields output_channels = hidden_channels * 2 = 128
        self.conv1 = TransformerConv(in_channels, hidden_channels, heads=2, concat=True, edge_dim=time_dim)
        self.bn1 = nn.BatchNorm1d(hidden_channels * 2)
        
        self.conv2 = TransformerConv(hidden_channels * 2, hidden_channels, heads=2, concat=True, edge_dim=time_dim)
        self.bn2 = nn.BatchNorm1d(hidden_channels * 2)
        
        # Last layer maps back to class channels with a single attention head
        self.conv3 = TransformerConv(hidden_channels * 2, out_channels, heads=1, concat=False, edge_dim=time_dim)
        self.dropout = nn.Dropout(0.3)

    def forward(self, x, edge_index, edge_attr=None, edge_timestamps=None):
        """
        Message passing over nodes using attention, raw edge features, and time encodings.
        """
        # Ensure fallback for edge attributes
        if edge_attr is None:
            edge_attr = torch.zeros((edge_index.size(1), 3), dtype=torch.float32, device=x.device)
            
        # Ensure fallback for edge timestamps (relative time velocity works perfectly)
        if edge_timestamps is None:
            edge_timestamps = edge_attr[:, 2]
            
        # 1. Compute time embeddings
        time_emb = self.time_encoder(edge_timestamps) # [E, time_dim]
        
        # 2. Combine projected edge features and time embeddings
        edge_features = self.edge_proj(edge_attr) + time_emb # [E, time_dim]
        
        # 3. Message passing layers
        x = self.conv1(x, edge_index, edge_features)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.conv2(x, edge_index, edge_features)
        x = self.bn2(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.conv3(x, edge_index, edge_features)
        return F.log_softmax(x, dim=1)

    def get_embedding(self, x, edge_index, edge_attr=None, edge_timestamps=None):
        """
        Extract internal node representations (embeddings) for downstream risk scoring.
        """
        if edge_attr is None:
            edge_attr = torch.zeros((edge_index.size(1), 3), dtype=torch.float32, device=x.device)
        if edge_timestamps is None:
            edge_timestamps = edge_attr[:, 2]
            
        time_emb = self.time_encoder(edge_timestamps)
        edge_features = self.edge_proj(edge_attr) + time_emb
        
        x = self.conv1(x, edge_index, edge_features)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.conv2(x, edge_index, edge_features)
        x = self.bn2(x)
        x = F.relu(x)
        return x

def train_gnn(model, data, labels, epochs=50):
    """
    Train helper for the Temporal GNN model.
    """
    device = next(model.parameters()).device
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    weights = torch.tensor([1.0, 50.0], device=device) 
    criterion = nn.NLLLoss(weight=weights)
    
    # Extract edge timestamps if present, else fallback
    edge_timestamps = None
    if hasattr(data, 'timestamp') and data.timestamp is not None:
        # Check if timestamp is a node or edge attribute
        if data.timestamp.size(0) == data.edge_index.size(1):
            edge_timestamps = data.timestamp.to(device)
        elif data.timestamp.size(0) == data.x.size(0):
            # Compute edge timestamps as the mean/max of connected node timestamps
            src, dst = data.edge_index[0], data.edge_index[1]
            edge_timestamps = (data.timestamp[src] + data.timestamp[dst]) / 2.0
            edge_timestamps = edge_timestamps.to(device)
            
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        
        # Pass edge_attr and edge_timestamps to forward pass
        edge_index = data.edge_index.to(device)
        edge_attr = data.edge_attr.to(device) if hasattr(data, 'edge_attr') and data.edge_attr is not None else None
        
        out = model(data.x.to(device), edge_index, edge_attr=edge_attr, edge_timestamps=edge_timestamps)
        loss = criterion(out, labels.to(device))
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f"Epoch {epoch}, Loss: {loss.item():.4f}")
