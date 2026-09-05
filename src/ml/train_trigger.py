import os
import logging
from src.system.swap_manager import swap_manager
from src.ml.train import train_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainTrigger")

def run_training_with_swap_protection(limit=None, device="cpu"):
    """
    Coordinates pre-training swap flushing of non-critical processes to maximize RAM
    prior to executing the main model training pipeline.
    """
    logger.info("====================================================")
    logger.info("  Starting training run with Selective RAM Protection")
    logger.info("====================================================")
    
    # 1. Trigger the aggressive swap flush of non-critical background processes
    try:
        if swap_manager.config.get("flush_on_train", True):
            logger.info("[SwapManager] Triggering pre-training swap flush...")
            metrics = swap_manager.flush_non_critical_processes()
            logger.info(f"[SwapManager] Swap flush complete. Metrics: {metrics}")
        else:
            logger.info("[SwapManager] Swap flush-on-train is disabled in config.")
    except Exception as e:
        logger.error(f"[SwapManager] Error during pre-training swap flush: {e}")
        
    # 2. Delegate to the core ML training pipeline
    try:
        train_pipeline(train_limit=limit, train_device=device)
    except Exception as e:
        logger.error(f"Error during training pipeline execution: {e}")
        raise e
