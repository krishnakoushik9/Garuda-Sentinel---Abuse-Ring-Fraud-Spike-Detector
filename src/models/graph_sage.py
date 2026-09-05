import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import pandas as pd
from pathlib import Path

# Compatibility bridge importing from modernized modules
from src.ml.models.gnn_model import MuleDetectionGNN, TimeEncoder, train_gnn
from src.pipeline.graph_builder import build_transaction_graph

