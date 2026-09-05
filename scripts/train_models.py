import os
from src.ml.train_trigger import run_training_with_swap_protection

def train_all():
    # Read TRAIN_TRANSACTION_LIMIT environment variable if present
    train_limit_raw = os.environ.get("TRAIN_TRANSACTION_LIMIT", "").strip()
    train_limit = int(train_limit_raw) if train_limit_raw else None
    
    # Read TRAIN_DEVICE environment variable
    train_device = os.environ.get("TRAIN_DEVICE", "cpu").strip()
    
    # Delegate to the training trigger with swap protection
    run_training_with_swap_protection(limit=train_limit, device=train_device)

if __name__ == "__main__":
    train_all()

