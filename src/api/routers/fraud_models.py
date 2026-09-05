import os
import time
import threading
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from src.ml import fraud_model_trainer
from src.config import ROOT

router = APIRouter(prefix="/fraud-models", tags=["BOI Fraud Models"])
logger = logging.getLogger("fraud_models_api")

# In-memory training status tracker
fraud_training_state = {
    "status": "idle",       # idle, training, completed, failed
    "current_step": "idle",
    "started_at": None,
    "finished_at": None,
    "logs": [],
    "metrics": {},
    "models_ready": [],
    "error": None
}

class TrainRequest(BaseModel):
    dataset_path: Optional[str] = "/home/krsna/Desktop/BOI/SETDATA/garuda_notebooks/DataSet.csv"

# Global lock to prevent concurrent training runs
training_lock = threading.Lock()

def background_training_task(dataset_path: str, output_dir: str):
    global fraud_training_state
    
    # Reset status
    fraud_training_state["status"] = "training"
    fraud_training_state["started_at"] = time.time()
    fraud_training_state["finished_at"] = None
    fraud_training_state["logs"] = []
    fraud_training_state["metrics"] = {}
    fraud_training_state["models_ready"] = []
    fraud_training_state["error"] = None
    
    def log_callback(msg: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {msg}"
        fraud_training_state["logs"].append(log_line)
        
        # Infer current step from message content
        if "Notebook 1" in msg or "Preprocessing" in msg:
            fraud_training_state["current_step"] = "preprocessing"
        elif "Notebook 2" in msg or "XGBoost" in msg:
            fraud_training_state["current_step"] = "xgboost"
        elif "Notebook 3" in msg or "LightGBM" in msg:
            fraud_training_state["current_step"] = "lightgbm"
        elif "Notebook 4" in msg or "Random Forest" in msg:
            fraud_training_state["current_step"] = "randomforest"
        elif "Notebook 5" in msg or "Isolation Forest" in msg:
            fraud_training_state["current_step"] = "isoforest"
        elif "Notebook 6" in msg or "MLP" in msg:
            fraud_training_state["current_step"] = "mlp"
        elif "Notebook 7" in msg or "Voting Ensemble" in msg:
            fraud_training_state["current_step"] = "ensemble"
            
        logger.info(log_line)

    try:
        # Step 1: Preprocessing
        log_callback("Starting Preprocessing & Feature Selection...")
        fraud_model_trainer.train("preprocessing", dataset_path, output_dir, log_callback)
        fraud_training_state["models_ready"].append("preprocessing")
        
        # Step 2: XGBoost
        log_callback("Training XGBoost Classifier...")
        metrics_xgb = fraud_model_trainer.train("xgboost", dataset_path, output_dir, log_callback)
        fraud_training_state["metrics"].update(metrics_xgb)
        fraud_training_state["models_ready"].append("xgboost")
        
        # Step 3: LightGBM
        log_callback("Training LightGBM Classifier...")
        metrics_lgb = fraud_model_trainer.train("lightgbm", dataset_path, output_dir, log_callback)
        fraud_training_state["metrics"].update(metrics_lgb)
        fraud_training_state["models_ready"].append("lightgbm")
        
        # Step 4: Random Forest
        log_callback("Training Random Forest Classifier...")
        metrics_rf = fraud_model_trainer.train("randomforest", dataset_path, output_dir, log_callback)
        fraud_training_state["metrics"].update(metrics_rf)
        fraud_training_state["models_ready"].append("randomforest")
        
        # Step 5: Isolation Forest
        log_callback("Training Isolation Forest Anomaly Detector...")
        metrics_iso = fraud_model_trainer.train("isoforest", dataset_path, output_dir, log_callback)
        fraud_training_state["metrics"].update(metrics_iso)
        fraud_training_state["models_ready"].append("isoforest")
        
        # Step 6: PyTorch MLP
        log_callback("Training PyTorch MLP Deep Neural Network...")
        metrics_mlp = fraud_model_trainer.train("mlp", dataset_path, output_dir, log_callback)
        fraud_training_state["metrics"].update(metrics_mlp)
        fraud_training_state["models_ready"].append("mlp")
        
        # Step 7: Voting Ensemble
        log_callback("Building Voting Ensemble Model...")
        metrics_ens = fraud_model_trainer.train("ensemble", dataset_path, output_dir, log_callback)
        fraud_training_state["metrics"].update(metrics_ens)
        fraud_training_state["models_ready"].append("ensemble")
        
        fraud_training_state["status"] = "completed"
        fraud_training_state["current_step"] = "completed"
        log_callback("BOI Fraud Detection model training pipeline finished successfully!")
        
    except Exception as e:
        logger.exception("Error running background training task")
        fraud_training_state["status"] = "failed"
        fraud_training_state["error"] = str(e)
        log_callback(f"Pipeline failed with error: {e}")
    finally:
        fraud_training_state["finished_at"] = time.time()


@router.post("/train", response_model=Dict[str, Any])
def trigger_training(req: Optional[TrainRequest] = None):
    """
    Triggers the end-to-end retraining of all 7 BOI Fraud detection steps in a background thread.
    """
    global fraud_training_state
    
    if fraud_training_state["status"] == "training":
        return {
            "status": "training",
            "message": "Model retraining is already in progress.",
            "started_at": fraud_training_state["started_at"]
        }
        
    dataset_path = req.dataset_path if req else "/home/krsna/Desktop/BOI/SETDATA/garuda_notebooks/DataSet.csv"
    output_dir = str(ROOT / "models" / "boi_fraud")
    
    if not os.path.exists(dataset_path):
        raise HTTPException(
            status_code=400, 
            detail=f"DataSet.csv was not found at specified path: {dataset_path}"
        )
        
    # Start thread
    thread = threading.Thread(
        target=background_training_task, 
        args=(dataset_path, output_dir),
        daemon=True
    )
    thread.start()
    
    return {
        "status": "training",
        "message": "BOI Fraud model training pipeline initiated successfully.",
        "started_at": time.time()
    }


@router.get("/status", response_model=Dict[str, Any])
def get_status():
    """
    Fetches the current status, progress logs, metrics, and list of ready models.
    """
    global fraud_training_state
    return fraud_training_state


class PredictRequest(BaseModel):
    features: Dict[str, Any]
    pipeline_type: Optional[str] = "boi"


@router.post("/predict", response_model=Dict[str, Any])
def run_prediction(req: PredictRequest):
    """
    Runs real-time prediction on the input feature dictionary using the trained ensemble model.
    """
    if req.pipeline_type == "core":
        try:
            import pandas as pd
            from src.models.xgboost_scorer import XGBoostScorer
            scorer = XGBoostScorer()
            cols = [
                'amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag',
                'night_txn_ratio', 'txn_velocity_1h', 'txn_velocity_24h', 'txn_velocity_7d',
                'unique_beneficiaries_7d', 'graph_degree_centrality', 'suspicious_neighbor_count', 'hop_2_mule_count'
            ]
            # Convert values to float where possible, default to 0.0
            float_features = {}
            for k, v in req.features.items():
                try:
                    float_features[k] = float(v)
                except (ValueError, TypeError):
                    float_features[k] = 0.0
                    
            df = pd.DataFrame([float_features])
            df = df.reindex(columns=cols, fill_value=0.0)
            
            # Score
            prob = float(scorer.score(df.values)[0])
            label = "FRAUD" if prob >= 0.5 else "LEGIT"
            return {
                "fraud_probability": round(prob, 4),
                "risk_label": label,
                "risk_score": round(prob * 100, 1),
                "pipeline": "core"
            }
        except Exception as e:
            logger.exception("Core prediction failure")
            raise HTTPException(status_code=500, detail=f"Core model prediction failed: {e}")

    # Default to the 7-model BOI ensemble
    output_dir = str(ROOT / "models" / "boi_fraud")
    ensemble_path = os.path.join(output_dir, "model_ensemble.pkl")
    
    if not os.path.exists(ensemble_path):
        raise HTTPException(
            status_code=400, 
            detail="Active Ensemble model not found on disk. Please trigger model training first."
        )
        
    try:
        # Load scaler, features list, and model
        scaler = fraud_model_trainer.load_model("scaler", output_dir)
        selected_features = fraud_model_trainer.load_model("selected_features", output_dir)
        ensemble = fraud_model_trainer.load_model("ensemble", output_dir)
        
        # Predict
        res = fraud_model_trainer.predict(ensemble, req.features, scaler, selected_features)
        res["pipeline"] = "boi"
        return res
    except Exception as e:
        logger.exception("Prediction failure")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")


@router.get("/download/{model_name}")
def download_model_file(model_name: str):
    """
    Serves the computed model .pkl or scaler files for manual local inspection.
    """
    output_dir = ROOT / "models" / "boi_fraud"
    
    if model_name == "scaler":
        filename = "scaler.pkl"
    elif model_name == "selected_features":
        filename = "selected_features.pkl"
    elif model_name in {"xgboost", "lightgbm", "randomforest", "isoforest", "mlp", "ensemble"}:
        filename = f"model_{model_name}.pkl"
    else:
        raise HTTPException(status_code=400, detail="Invalid model identifier requested.")
        
    filepath = output_dir / filename
    if not filepath.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Requested artifact '{filename}' not found. Please train models first."
        )
        
    return FileResponse(
        path=str(filepath), 
        filename=filename, 
        media_type="application/octet-stream"
    )
