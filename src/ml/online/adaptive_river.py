import os
import json
import joblib
import sqlite3
import numpy as np
from datetime import datetime
from river.forest import ARFClassifier
from river.drift import ADWIN
from src.config import SQLITE_DB_PATH

class AdaptiveRiverModel:
    """
    Real-time online learning system powered by River's ARFClassifier (Adaptive Random Forest)
    paired with an ADWIN drift detector. Continuously adapts to concept drift in streaming transactional feeds.
    """
    def __init__(self, model_path="models/adaptive_river.pkl", metrics_path="models/river_metrics.json"):
        self.model_path = model_path
        self.metrics_path = metrics_path
        self.model = None
        self.update_count = 0
        self.correct_predictions = 0
        self.total_seen = 0
        
        self.init_model()

    def init_model(self):
        """Loads a persisted online model state or initializes a new ARFClassifier."""
        if os.path.exists(self.model_path):
            try:
                state = joblib.load(self.model_path)
                self.model = state['model']
                self.update_count = state.get('update_count', 0)
                self.correct_predictions = state.get('correct_predictions', 0)
                self.total_seen = state.get('total_seen', 0)
                print(f"[RIVER] Successfully loaded online classifier (updates processed: {self.update_count})")
                return
            except Exception as e:
                print(f"[RIVER] Failed to load cached model state: {e}. Resetting...")
                
        # Initialize the Adaptive Random Forest Classifier (25 models) with ADWIN drift detector
        self.model = ARFClassifier(
            n_models=25,
            drift_detector=ADWIN(),
            seed=42
        )
        self.update_count = 0
        self.correct_predictions = 0
        self.total_seen = 0
        print("[RIVER] Brand new ARFClassifier and ADWIN drift detector initialized.")

    def learn_one(self, features: dict, label: int):
        """
        Performs online learning on a single confirmed transaction instance.
        Converts the features and updates the estimator parameters in real-time.
        """
        # Predict class pre-update to compute online stream accuracy metric
        pred_probs = self.model.predict_proba_one(features)
        pred_label = self.model.predict_one(features)
        
        # Learn from confirmed analyst classification
        self.model.learn_one(features, int(label))
        
        self.update_count += 1
        self.total_seen += 1
        
        if pred_label is not None and int(pred_label) == int(label):
            self.correct_predictions += 1
            
        # Check and trigger validation against the batch stacking model every 1000 confirmed updates
        if self.update_count % 1000 == 0:
            self.evaluate_and_log_performance()
            
        self.save()
        
        # Return online probability score for 1 (fraud)
        return float(pred_probs.get(1, 0.0)) if pred_probs else 0.0

    def predict_proba_one(self, features: dict) -> float:
        """Returns the probability score of fraud (class 1) for a single dict of features."""
        if self.model is None:
            self.init_model()
        probs = self.model.predict_proba_one(features)
        return float(probs.get(1, 0.0)) if probs else 0.0

    def evaluate_and_log_performance(self):
        """Validates the online classifier's performance against the batch model and logs it."""
        print(f"[RIVER] Running comparison against batch stacking classifier at {self.update_count} updates...")
        online_acc = self.correct_predictions / max(1, self.total_seen)
        
        batch_acc = 0.0
        try:
            stacking_path = "models/ensemble_stacking.pkl"
            if os.path.exists(stacking_path):
                stacking_clf = joblib.load(stacking_path)
                
                # Retrieve recent transaction feature cached records for testing
                conn = sqlite3.connect(SQLITE_DB_PATH)
                conn.row_factory = sqlite3.Row
                
                mule_rows = conn.execute("SELECT account_id FROM mule_accounts").fetchall()
                mule_ids = {r['account_id'] for r in mule_rows}
                
                rows = conn.execute("SELECT * FROM transaction_features ORDER BY ROWID DESC LIMIT 200").fetchall()
                conn.close()
                
                if rows:
                    features_list = []
                    labels_list = []
                    for r in rows:
                        features_list.append([
                            r['amount_zscore'], r['is_new_beneficiary'], r['fan_out_ratio'],
                            r['dormancy_break_flag'], r['night_txn_ratio'], r['txn_velocity_1h'],
                            r['txn_velocity_24h'], r['txn_velocity_7d'], r['unique_beneficiaries_7d'],
                            r['graph_degree_centrality'], r['suspicious_neighbor_count'], r['hop_2_mule_count']
                        ])
                        labels_list.append(1 if r['account_id'] in mule_ids else 0)
                        
                    X = np.array(features_list)
                    y = np.array(labels_list)
                    
                    batch_preds = stacking_clf.predict(X)
                    batch_acc = float(np.mean(batch_preds == y))
        except Exception as e:
            print(f"[RIVER] Batch comparison log skipped: {e}")
            
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "updates": self.update_count,
            "online_accuracy": online_acc,
            "batch_accuracy": batch_acc,
            "timestamp_epoch": int(datetime.now().timestamp())
        }
        
        # Load and append to JSON metric logs
        log_data = []
        if os.path.exists(self.metrics_path):
            try:
                with open(self.metrics_path, "r") as f:
                    log_data = json.load(f)
            except Exception:
                pass
                
        log_data.append(log_entry)
        
        # Ensure log folder exists
        os.makedirs(os.path.dirname(self.metrics_path), exist_ok=True)
        with open(self.metrics_path, "w") as f:
            json.dump(log_data, f, indent=4)
            
        print(f"[RIVER LOG SUCCESS] Online Accuracy: {online_acc:.4f} | Batch Accuracy: {batch_acc:.4f}")

    def save(self):
        """Persists the state of the online estimator."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        state = {
            'model': self.model,
            'update_count': self.update_count,
            'correct_predictions': self.correct_predictions,
            'total_seen': self.total_seen
        }
        joblib.dump(state, self.model_path)
