import os
import joblib
import sqlite3
import numpy as np
from sklearn.ensemble import IsolationForest
from src.config import SQLITE_DB_PATH

class RealTimeIsolationForest:
    """
    Unsupervised zero-day anomaly detection engine using scikit-learn's Isolation Forest.
    Trains on normal transactions features to identify outliers outside of known patterns.
    """
    def __init__(self, model_path="models/isolation_forest.pkl", threshold=0.15):
        self.model_path = model_path
        self.threshold = threshold  # Anomaly score threshold (anomaly_score = -decision_function)
        self.model = None
        
        # Self-initialize and train if not pre-trained
        self.init_model()

    def init_model(self):
        """Loads a cached Isolation Forest model, otherwise trains a new one."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"[IFOREST] Pre-trained Isolation Forest loaded from {self.model_path}")
                return
            except Exception as e:
                print(f"[IFOREST] Load failed: {e}. Re-training model...")
                
        self.train()

    def train(self):
        """Trains the Isolation Forest on normal transaction feature records (unsupervised)."""
        print("[IFOREST] Beginning unsupervised model initialization & training...")
        features_list = []
        
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            
            # Load known mule account IDs to exclude them from normal baseline training
            mule_rows = conn.execute("SELECT account_id FROM mule_accounts").fetchall()
            mule_ids = {r['account_id'] for r in mule_rows}
            
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transaction_features'")
            if cursor.fetchone():
                # Read features cached in sqlite
                rows = conn.execute("SELECT * FROM transaction_features LIMIT 25000").fetchall()
                for r in rows:
                    if r['account_id'] not in mule_ids:
                        features_list.append([
                            r['amount_zscore'], r['is_new_beneficiary'], r['fan_out_ratio'],
                            r['dormancy_break_flag'], r['night_txn_ratio'], r['txn_velocity_1h'],
                            r['txn_velocity_24h'], r['txn_velocity_7d'], r['unique_beneficiaries_7d'],
                            r['graph_degree_centrality'], r['suspicious_neighbor_count'], r['hop_2_mule_count']
                        ])
            conn.close()
        except Exception as e:
            print(f"[IFOREST] Warning: Failed to retrieve normal transaction features from sqlite: {e}")
            
        # Fallback to generating highly realistic synthetic normal data if training set is too small
        if len(features_list) < 100:
            print(f"[IFOREST] Insufficient historical data ({len(features_list)} rows). Generating synthetic normal features...")
            # 12 normal feature columns
            normal_data = np.random.randn(2000, 12) * 0.8
            # Align features with standard distributions
            normal_data[:, 1] = np.random.choice([0.0, 1.0], size=2000, p=[0.85, 0.15]) # is_new_beneficiary
            normal_data[:, 3] = np.random.choice([0.0, 1.0], size=2000, p=[0.99, 0.01]) # dormancy_break_flag
            features_list = normal_data.tolist()
            
        X = np.array(features_list)
        
        # Fit Isolation Forest
        self.model = IsolationForest(
            n_estimators=100,
            max_samples='auto',
            contamination=0.01,  # 1% expected outlier contamination
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X)
        
        # Persist trained model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f"[IFOREST] Unsupervised Isolation Forest model successfully saved to {self.model_path}")

    def score(self, features_array: np.ndarray) -> float:
        """
        Calculates the anomaly score for a given transaction.
        Higher score indicates higher outlier probability (typically > 0.15 is highly anomalous).
        """
        if self.model is None:
            self.init_model()
            
        if features_array.ndim == 1:
            features_array = features_array.reshape(1, -1)
            
        # Decision function returns negative for outliers, positive for inliers.
        # Opposites of decision_function yields: higher values = higher anomaly.
        decision = self.model.decision_function(features_array)
        anomaly_score = float(-decision[0])
        return anomaly_score
