import os
import joblib
import sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb
from src.config import SQLITE_DB_PATH

class FastVotingEnsemble:
    """
    Tier 1 Soft-Voting Ensemble combining a lightweight XGBoost, a sparse Logistic Regression,
    and a decision tree representing heuristic patterns. Designed for sub-millisecond latency (<1ms).
    """
    def __init__(self, model_path="models/ensemble_voting.pkl"):
        self.model_path = model_path
        self.model = None
        self.init_model()

    def init_model(self):
        """Loads the pre-trained voting classifier, or trains a new one dynamically if missing."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"[VOTING] Loaded pre-trained voting ensemble from {self.model_path}")
                return
            except Exception as e:
                print(f"[VOTING] Load failed: {e}. Re-training ensemble...")
                
        self.train()

    def train(self):
        """Trains base classifiers and voting ensemble on cached SQLite feature vectors."""
        print("[VOTING] Training fast voting ensemble estimators...")
        features_list = []
        labels_list = []
        
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            
            # Load known mule account IDs for target labeling
            mule_rows = conn.execute("SELECT account_id FROM mule_accounts").fetchall()
            mule_ids = {r['account_id'] for r in mule_rows}
            
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transaction_features'")
            if cursor.fetchone():
                rows = conn.execute("SELECT * FROM transaction_features LIMIT 35000").fetchall()
                for r in rows:
                    features_list.append([
                        r['amount_zscore'], r['is_new_beneficiary'], r['fan_out_ratio'],
                        r['dormancy_break_flag'], r['night_txn_ratio'], r['txn_velocity_1h'],
                        r['txn_velocity_24h'], r['txn_velocity_7d'], r['unique_beneficiaries_7d'],
                        r['graph_degree_centrality'], r['suspicious_neighbor_count'], r['hop_2_mule_count']
                    ])
                    
                    # Label 1 if account is a known mule
                    is_mule = 1.0 if r['account_id'] in mule_ids else 0.0
                    labels_list.append(is_mule)
            conn.close()
        except Exception as e:
            print(f"[VOTING] Warning during SQLite data loading: {e}")
            
        # Fallback to synthetic training distributions if dataset is empty
        if len(features_list) < 100:
            print("[VOTING] Insufficient dataset rows. Utilizing synthetic distributions for ensemble fit...")
            # Normal distribution
            X_normal = np.random.randn(1000, 12) * 0.5
            y_normal = np.zeros(1000)
            # Fraud distribution
            X_fraud = np.random.randn(200, 12) * 1.5 + 2.0
            y_fraud = np.ones(200)
            
            X = np.vstack([X_normal, X_fraud])
            y = np.concatenate([y_normal, y_fraud])
        else:
            X = np.array(features_list)
            y = np.array(labels_list)
            
        # Ensure y has binary classes present
        if len(np.unique(y)) < 2:
            y[0] = 1.0 # Force active classes
            
        # Base estimators
        xgb_fast = xgb.XGBClassifier(
            n_estimators=30,
            max_depth=3,
            learning_rate=0.15,
            eval_metric='logloss',
            random_state=42
        )
        lite_lr = LogisticRegression(
            class_weight='balanced',
            max_iter=300,
            random_state=42
        )
        dt_rules = DecisionTreeClassifier(
            max_depth=4,
            class_weight='balanced',
            random_state=42
        )
        
        # Assemble VotingClassifier
        self.model = VotingClassifier(
            estimators=[
                ('xgb', xgb_fast),
                ('lr', lite_lr),
                ('dt', dt_rules)
            ],
            voting='soft',
            weights=[0.6, 0.2, 0.2]
        )
        
        self.model.fit(X, y)
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f"[VOTING] Soft-voting ensemble successfully saved to {self.model_path}")

    def predict_proba(self, X) -> np.ndarray:
        """Returns class probabilities. Shape [N, 2]."""
        if self.model is None:
            self.init_model()
            
        if X.ndim == 1:
            X = X.reshape(1, -1)
            
        return self.model.predict_proba(X)

    def score_and_confidence(self, X) -> tuple:
        """
        Scores input and returns the predicted probability and model confidence.
        Confidence is defined as max(p, 1 - p), measuring distance from boundary.
        """
        probs = self.predict_proba(X)[0]
        fraud_prob = float(probs[1])
        confidence = float(np.max(probs))
        return fraud_prob, confidence
