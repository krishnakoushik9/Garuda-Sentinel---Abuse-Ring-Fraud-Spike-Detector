import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import average_precision_score, precision_recall_curve
import shap
import joblib
from pathlib import Path

class XGBoostScorer:
    def __init__(self, model_path: str = None, calibrated_model_path: str = None):
        self.root = Path(__file__).resolve().parents[2]
        self.model_path = model_path or str(self.root / "models" / "xgb_fraud.json")
        self.calibrated_model_path = calibrated_model_path or str(self.root / "models" / "xgb_calibrated.pkl")
        self.model = None
        self.calibrated_model = None
        self.explainer = None

    def generate_synthetic_data(self, n_samples=100000, fraud_rate=0.001):
        """Generate synthetic feature data for training."""
        n_fraud = int(n_samples * fraud_rate)
        n_normal = n_samples - n_fraud
        
        # Features: amount_zscore, is_new_beneficiary, fan_out_ratio, dormancy_break_flag, 
        # night_txn_ratio, txn_velocity_1h, txn_velocity_24h, txn_velocity_7d, 
        # unique_beneficiaries_7d, graph_degree_centrality, suspicious_neighbor_count, hop_2_mule_count
        
        # Normal data
        X_normal = np.random.randn(n_normal, 12)
        X_normal[:, 1] = np.random.choice([0, 1], size=n_normal, p=[0.8, 0.2]) # is_new_beneficiary
        X_normal[:, 3] = np.random.choice([0, 1], size=n_normal, p=[0.99, 0.01]) # dormancy_break
        
        # Fraud data (shift distributions)
        X_fraud = np.random.randn(n_fraud, 12) + 2.0
        X_fraud[:, 1] = np.random.choice([0, 1], size=n_fraud, p=[0.3, 0.7])
        X_fraud[:, 3] = np.random.choice([0, 1], size=n_fraud, p=[0.8, 0.2])
        X_fraud[:, 5:8] += 5.0 # High velocity
        
        X = np.vstack([X_normal, X_fraud])
        y = np.array([0] * n_normal + [1] * n_fraud)
        
        columns = [
            'amount_zscore', 'is_new_beneficiary', 'fan_out_ratio', 'dormancy_break_flag',
            'night_txn_ratio', 'txn_velocity_1h', 'txn_velocity_24h', 'txn_velocity_7d',
            'unique_beneficiaries_7d', 'graph_degree_centrality', 'suspicious_neighbor_count', 'hop_2_mule_count'
        ]
        return pd.DataFrame(X, columns=columns), y

    def train(self, X, y):
        """Train and Calibrate the XGBoost model."""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # scale_pos_weight for imbalanced classes
        self.model = xgb.XGBClassifier(
            scale_pos_weight=999,
            tree_method='hist',
            eval_metric='aucpr',
            use_label_encoder=False,
            n_estimators=100
        )
        
        self.model.fit(X_train, y_train)
        
        # Save base model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.model.save_model(self.model_path)
        print(f"Base model saved to {self.model_path}")
        
        # Calibrate using CalibratedClassifierCV with cv=3
        from sklearn.calibration import CalibratedClassifierCV
        print("Calibrating model using CalibratedClassifierCV(cv=3)...")
        self.calibrated_model = CalibratedClassifierCV(
            estimator=self.model,
            method='isotonic',
            cv=3
        )
        self.calibrated_model.fit(X_train, y_train)
        
        # Save calibrated model to pkl
        os.makedirs(os.path.dirname(self.calibrated_model_path), exist_ok=True)
        joblib.dump(self.calibrated_model, self.calibrated_model_path)
        print(f"Calibrated model saved to {self.calibrated_model_path}")
        
        y_prob = self.calibrated_model.predict_proba(X_test)[:, 1]
        aucpr = average_precision_score(y_test, y_prob)
        print(f"Training & Calibration complete. Calibrated AUCPR: {aucpr:.4f}")
        
        # Initialize SHAP
        self.explainer = shap.TreeExplainer(self.model)

    def load(self):
        """Load the calibrated model preferentially, falling back to base model if necessary."""
        if os.path.exists(self.calibrated_model_path):
            self.calibrated_model = joblib.load(self.calibrated_model_path)
            print(f"Loaded calibrated XGBoost model from {self.calibrated_model_path}")
            # Get underlying base model for SHAP explanations
            try:
                self.model = self.calibrated_model.estimator
            except AttributeError:
                try:
                    self.model = self.calibrated_model.calibrated_classifiers_[0].estimator
                except Exception:
                    self.model = None
        
        if self.model is None and os.path.exists(self.model_path):
            self.model = xgb.XGBClassifier()
            self.model.load_model(self.model_path)
            print(f"Loaded base XGBoost model from {self.model_path}")
            
        if self.model is not None:
            self.explainer = shap.TreeExplainer(self.model)
        else:
            print("Warning: No model files found to load. Please run train first.")

    def score(self, X):
        """Return calibrated fraud probabilities if available, otherwise base model probabilities."""
        if self.calibrated_model is None and self.model is None:
            self.load()
            
        if self.calibrated_model is not None:
            return self.calibrated_model.predict_proba(X)[:, 1]
        elif self.model is not None:
            return self.model.predict_proba(X)[:, 1]
        else:
            raise ValueError("No model loaded.")

    def explain(self, X):
        """Return SHAP values for explanation."""
        if self.explainer is None: self.load()
        if self.explainer is not None:
            return self.explainer.shap_values(X)
        else:
            raise ValueError("TreeExplainer could not be initialized because base model is not loaded.")

if __name__ == "__main__":
    print("--- XGBoostScorer Demo ---")
    scorer = XGBoostScorer()
    X, y = scorer.generate_synthetic_data(n_samples=10000)
    scorer.train(X, y)
    
    # Predict on a few samples
    sample_X = X.head(5)
    probs = scorer.score(sample_X)
    shap_vals = scorer.explain(sample_X)
    
    print("\nSample Probabilities:", probs)
    print("SHAP Values Shape:", shap_vals.shape)
