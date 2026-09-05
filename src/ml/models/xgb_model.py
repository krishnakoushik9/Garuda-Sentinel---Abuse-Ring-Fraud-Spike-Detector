import os
import joblib
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from pathlib import Path

class XGBoostTrainer:
    def __init__(self, model_path: str = None, calibrated_path: str = None):
        self.root = Path(__file__).resolve().parents[3]
        self.model_path = model_path or str(self.root / "models" / "xgb_fraud.json")
        self.calibrated_path = calibrated_path or str(self.root / "models" / "xgb_calibrated.pkl")
        self.model = None
        self.calibrated_model = None

    def train(self, X_train, y_train, scale_pos_weight=1.0, device='cpu'):
        """
        Train the base XGBoost model using the standard historical settings.
        """
        print(f"[XGBoost] Training base classifier with scale_pos_weight={scale_pos_weight:.4f} on device={device}")
        self.model = xgb.XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            tree_method='hist',
            device=device,
            eval_metric='aucpr',
            use_label_encoder=False,
            n_estimators=50,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # Save base model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self.model.save_model(self.model_path)
        print(f"[XGBoost] Base model successfully saved to {self.model_path}")
        return self.model

    def calibrate(self, X_train, y_train):
        """
        Calibrate the trained XGBoost model using CalibratedClassifierCV with cv=3.
        """
        if self.model is None:
            raise ValueError("[XGBoost] Base model must be trained prior to calibration.")
            
        print("[XGBoost] Calibrating XGBoost model probabilities using CalibratedClassifierCV (cv=3)...")
        # Calibrate using isotonic regression
        self.calibrated_model = CalibratedClassifierCV(
            estimator=self.model,
            method='isotonic',
            cv=3
        )
        self.calibrated_model.fit(X_train, y_train)
        
        # Save calibrated model to pkl
        os.makedirs(os.path.dirname(self.calibrated_path), exist_ok=True)
        joblib.dump(self.calibrated_model, self.calibrated_path)
        print(f"[XGBoost] Calibrated model successfully saved to {self.calibrated_path}")
        return self.calibrated_model
