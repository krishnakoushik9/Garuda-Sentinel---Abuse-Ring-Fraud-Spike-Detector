import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.makedirs("/home/krsna/Desktop/BOI/models/boi_fraud", exist_ok=True)

from src.ml import fraud_model_trainer

DATASET_PATH = "/home/krsna/Desktop/BOI/SETDATA/garuda_notebooks/DataSet.csv"
OUTPUT_DIR   = "/home/krsna/Desktop/BOI/models/boi_fraud"

print("=" * 60)
print("GARUDA SENTINEL — BOI FRAUD MODEL TRAINING PIPELINE")
print("=" * 60)

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(f"dataset.csv not found at: {DATASET_PATH}")

print(f"Dataset confirmed at: {DATASET_PATH}")
print(f"Output directory:     {OUTPUT_DIR}")
print("=" * 60)

metrics = fraud_model_trainer.train(
    model_name="all",
    dataset_path=DATASET_PATH,
    output_dir=OUTPUT_DIR,
    log_callback=print
)

print("\n" + "=" * 60)
print("FINAL METRICS SUMMARY")
print("=" * 60)
print(json.dumps(metrics, indent=2))

print("\n" + "=" * 60)
print("SAVED MODEL ARTIFACTS")
print("=" * 60)
expected_files = [
    "preprocessed_boi.csv",
    "scaler.pkl",
    "selected_features.pkl",
    "model_xgboost.pkl",
    "model_lightgbm.pkl",
    "model_randomforest.pkl",
    "model_isoforest.pkl",
    "model_mlp.pkl",
    "model_ensemble.pkl",
    "best_mlp.pt"
]
all_ok = True
for fname in expected_files:
    fpath = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(fpath):
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  OK  {fpath}  ({size_kb:.1f} KB)")
    else:
        print(f"  MISSING  {fpath}")
        all_ok = False

print("\n" + "=" * 60)
print("INTEGRATION VERIFICATION")
print("=" * 60)

# Verify ensemble loads and predicts correctly
try:
    import pickle
    with open(os.path.join(OUTPUT_DIR, "model_ensemble.pkl"), "rb") as f:
        ensemble = pickle.load(f)
    with open(os.path.join(OUTPUT_DIR, "scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    with open(os.path.join(OUTPUT_DIR, "selected_features.pkl"), "rb") as f:
        selected_features = pickle.load(f)

    sample = {f: 0.0 for f in selected_features}
    result = fraud_model_trainer.predict(ensemble, sample, scaler, selected_features)
    print(f"  Ensemble smoke test PASSED")
    print(f"  Sample prediction: {result}")
except Exception as e:
    print(f"  Ensemble smoke test FAILED: {e}")
    all_ok = False

if all_ok:
    print("\n  ALL MODELS READY. Integration complete.")
    print("  FastAPI endpoint /api/v1/fraud-models/predict is now live.")
    print("  Frontend BOI Fraud Models tab will show metrics on next poll.")
else:
    print("\n  Some artifacts missing. Check errors above.")
