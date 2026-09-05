import os
import re
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_classif
from sklearn.impute import KNNImputer
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from imblearn.over_sampling import SMOTE
from imblearn.combine import SMOTETomek
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler

# ── MLP CUSTOM CLASSES (Must be at module level for pickle serialization) ──

class FocalLoss(nn.Module):
    def __init__(self, alpha=0.25, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, inputs, targets):
        bce = nn.functional.binary_cross_entropy_with_logits(
            inputs, targets.float(), reduction='none')
        pt = torch.exp(-bce)
        focal = self.alpha * (1 - pt) ** self.gamma * bce
        return focal.mean()

class FraudMLP(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

    def forward(self, x):
        return self.net(x).squeeze(1)

class MLPWrapper:
    def __init__(self, model, device_name):
        self.model = model
        self.device_name = device_name
        
    @property
    def device(self):
        return torch.device(self.device_name)
        
    def predict_proba(self, X):
        self.model.eval()
        t = torch.tensor(X.astype(np.float32)).to(self.device)
        with torch.no_grad():
            p = torch.sigmoid(self.model(t)).cpu().numpy()
        return np.column_stack([1 - p, p])
        
    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

# ── ENSEMBLE CUSTOM CLASS ──

class EnsembleModel:
    def __init__(self, models, weights, iso_min=0.0, iso_max=1.0):
        self.models = models
        self.weights = weights
        self.iso_min = iso_min
        self.iso_max = iso_max

    def predict_proba_from_X(self, X):
        probs = {}
        for name, mdl in self.models.items():
            if name == 'isoforest':
                # Anomaly scores: lower is more anomalous. So flip it.
                raw = -mdl.score_samples(X)
                denom = self.iso_max - self.iso_min
                if denom == 0:
                    denom = 1e-5
                # Normalise to [0, 1] range using training calibration limits
                probs[name] = np.clip((raw - self.iso_min) / denom, 0.0, 1.0)
            else:
                probs[name] = mdl.predict_proba(X)[:, 1]
                
        ep = np.zeros(len(X))
        tw = 0
        for name, p in probs.items():
            w = self.weights.get(name, 0.2)
            ep += w * p
            tw += w
        return ep / tw

    def predict(self, X):
        return (self.predict_proba_from_X(X) >= 0.5).astype(int)

# ── TRAINER ENGINE ──

BOI_FEATURES = [
    'F115', 'F321', 'F527', 'F531', 'F670', 'F1692', 'F2082', 'F2122',
    'F2582', 'F2678', 'F2737', 'F2956', 'F3043', 'F3836', 'F3887',
    'F3889', 'F3891', 'F3894'
]

def train(model_name: str, dataset_path: str, output_dir: str, log_callback=None) -> dict:
    """
    Modular training driver containing all 7 pipeline components.
    Saves outputs to output_dir and returns computed metrics.
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    os.makedirs(output_dir, exist_ok=True)
    
    # ── 1. PREPROCESSING ──
    if model_name == "preprocessing" or model_name == "all":
        log(f"--- Notebook 1: Preprocessing + Feature Selection ---")
        log(f"Loading raw dataset from {dataset_path}...")
        df = pd.read_csv(dataset_path)
        log(f"Raw shape: {df.shape}")
        
        TARGET = df.columns[-1]
        X_raw = df.drop(columns=[TARGET])
        y = df[TARGET].astype(int)
        
        log(f"Class distribution: {y.value_counts().to_dict()}")
        log(f"Fraud rate: {y.mean()*100:.4f}%")
        
        # Convert object columns to numeric (factorize) and preserve missing flags
        categorical_mappings = {}
        X_encoded = X_raw.copy()
        for col in X_encoded.select_dtypes(include=['object']).columns:
            mask = X_encoded[col].isna()
            labels, uniques = pd.factorize(X_encoded[col])
            X_encoded[col] = np.where(mask, np.nan, labels)
            categorical_mappings[col] = list(uniques)
            log(f"Factorized categorical column: {col} ({len(uniques)} unique values)")
            
        # Save mappings for prediction time
        mappings_path = os.path.join(output_dir, "categorical_mappings.pkl")
        with open(mappings_path, "wb") as f:
            pickle.dump(categorical_mappings, f)
            
        null_pct = X_encoded.isnull().mean()
        drop_cols = null_pct[null_pct > 0.60].index.tolist()
        X = X_encoded.drop(columns=drop_cols)
        log(f"Dropped {len(drop_cols)} columns with >60% null values. Remaining: {X.shape[1]}")
        
        high_null = null_pct[(null_pct > 0.05) & (null_pct <= 0.60)].index.tolist()
        high_null = [c for c in high_null if c in X.columns]
        low_null = null_pct[(null_pct > 0) & (null_pct <= 0.05)].index.tolist()
        low_null = [c for c in low_null if c in X.columns]
        
        for col in low_null:
            X[col].fillna(X[col].median(), inplace=True)
            
        if high_null:
            log(f"Imputing {len(high_null)} moderate-null columns using KNNImputer (this may take 2-3 mins)...")
            imputer = KNNImputer(n_neighbors=5)
            X[high_null] = imputer.fit_transform(X[high_null])
            
        X.fillna(0, inplace=True)
        
        boi_present = [f for f in BOI_FEATURES if f in X.columns]
        log(f"BOI features present: {len(boi_present)}/{len(BOI_FEATURES)}")
        
        log("Computing Mutual Information feature selection (top 100)...")
        mi_scores = mutual_info_classif(X, y, random_state=42)
        mi_series = pd.Series(mi_scores, index=X.columns).sort_values(ascending=False)
        top_mi = mi_series.head(100).index.tolist()
        
        selected_features = list(set(top_mi + boi_present))
        log(f"Selected {len(selected_features)} features (top-100 MI + present BOI features)")
        
        X_sel = X[selected_features]
        # Sanitize feature names to prevent LightGBM JSON/special characters exceptions
        X_sel = X_sel.rename(columns=lambda x: re.sub(r'[\[\]<>,":\{\}\s]', '_', x))
        selected_features = X_sel.columns.tolist()
        
        scaler = StandardScaler()
        X_scaled = pd.DataFrame(scaler.fit_transform(X_sel), columns=selected_features)
        X_scaled['TARGET'] = y.values
        
        # Save artifacts
        preprocessed_path = os.path.join(output_dir, "preprocessed_boi.csv")
        scaler_path = os.path.join(output_dir, "scaler.pkl")
        features_path = os.path.join(output_dir, "selected_features.pkl")
        
        X_scaled.to_csv(preprocessed_path, index=False)
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)
        with open(features_path, "wb") as f:
            pickle.dump(selected_features, f)
            
        log("Successfully saved: preprocessed_boi.csv | scaler.pkl | selected_features.pkl")
        
        if model_name == "preprocessing":
            return {"status": "success", "features_selected": len(selected_features)}

    # Ensure preprocessed data exists for model training
    preprocessed_path = os.path.join(output_dir, "preprocessed_boi.csv")
    if not os.path.exists(preprocessed_path):
        raise FileNotFoundError("Preprocessed data not found. Please run preprocessing first.")
        
    df = pd.read_csv(preprocessed_path)
    X = df.drop(columns=['TARGET'])
    y = df['TARGET']
    
    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    metrics = {}

    # ── 2. XGBOOST ──
    if model_name == "xgboost" or model_name == "all":
        log("--- Notebook 2: XGBoost with SMOTE ---")
        sm = SMOTE(random_state=42, k_neighbors=5)
        X_res, y_res = sm.fit_resample(X_train, y_train)
        
        model = XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=1,
            eval_metric='aucpr',
            use_label_encoder=False,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_res, y_res)
        
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        f1 = f1_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob)
        
        log(f"XGBoost Test Metrics -> F1: {f1:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | ROC-AUC: {auc:.4f}")
        
        model_path = os.path.join(output_dir, "model_xgboost.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        metrics["xgboost"] = {"F1": f1, "Precision": prec, "Recall": rec, "ROC-AUC": auc}

    # ── 3. LIGHTGBM ──
    if model_name == "lightgbm" or model_name == "all":
        log("--- Notebook 3: LightGBM ---")
        sm = SMOTE(random_state=42)
        X_res, y_res = sm.fit_resample(X_train, y_train)
        
        model = LGBMClassifier(
            n_estimators=1000,
            num_leaves=63,
            max_depth=-1,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_samples=20,
            class_weight='balanced',
            n_jobs=-1,
            random_state=42,
            verbose=-1
        )
        # Avoid early stopping failures if test dataset has too few frauds
        try:
            from lightgbm import early_stopping, log_evaluation
            model.fit(
                X_res, y_res,
                eval_set=[(X_test, y_test)],
                callbacks=[early_stopping(50, verbose=False), log_evaluation(0)]
            )
        except Exception:
            model.fit(X_res, y_res)
            
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        f1 = f1_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob)
        
        log(f"LightGBM Test Metrics -> F1: {f1:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | ROC-AUC: {auc:.4f}")
        
        model_path = os.path.join(output_dir, "model_lightgbm.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        metrics["lightgbm"] = {"F1": f1, "Precision": prec, "Recall": rec, "ROC-AUC": auc}

    # ── 4. RANDOM FOREST ──
    if model_name == "randomforest" or model_name == "all":
        log("--- Notebook 4: Random Forest ---")
        smt = SMOTETomek(random_state=42)
        X_res, y_res = smt.fit_resample(X_train, y_train)
        
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=20,
            min_samples_leaf=2,
            class_weight='balanced_subsample',
            n_jobs=-1,
            random_state=42
        )
        model.fit(X_res, y_res)
        
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        f1 = f1_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob)
        
        log(f"Random Forest Test Metrics -> F1: {f1:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | ROC-AUC: {auc:.4f}")
        
        model_path = os.path.join(output_dir, "model_randomforest.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        metrics["randomforest"] = {"F1": f1, "Precision": prec, "Recall": rec, "ROC-AUC": auc}

    # ── 5. ISOLATION FOREST ──
    if model_name == "isoforest" or model_name == "all":
        log("--- Notebook 5: Isolation Forest ---")
        # Train on legit only
        X_legit_train = X_train[y_train == 0]
        fraud_rate = max(1e-4, float(y.mean()))
        
        model = IsolationForest(
            n_estimators=300,
            contamination=fraud_rate,
            max_features=0.8,
            bootstrap=True,
            n_jobs=-1,
            random_state=42
        )
        model.fit(X_legit_train)
        
        # Isolation Forest outputs -1 (anomaly) and 1 (normal)
        raw_pred = model.predict(X_test)
        y_pred = (raw_pred == -1).astype(int)
        
        # Scores (higher = more anomalous)
        scores = -model.score_samples(X_test)
        
        f1 = f1_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, scores)
        
        log(f"Isolation Forest Test Metrics -> F1: {f1:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | ROC-AUC: {auc:.4f}")
        
        model_path = os.path.join(output_dir, "model_isoforest.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        metrics["isoforest"] = {"F1": f1, "Precision": prec, "Recall": rec, "ROC-AUC": auc}

    # ── 6. PyTorch MLP ──
    if model_name == "mlp" or model_name == "all":
        log("--- Notebook 6: MLP Neural Network ---")
        
        X_train_np = X_train.values.astype(np.float32)
        y_train_np = y_train.values.astype(np.float32)
        X_test_np = X_test.values.astype(np.float32)
        y_test_np = y_test.values.astype(np.float32)
        
        class_counts = np.bincount(y_train.values.astype(int))
        class_counts = np.maximum(class_counts, 1) # Avoid zero divs
        weights = 1.0 / class_counts[y_train.values.astype(int)]
        sampler = WeightedRandomSampler(weights, len(weights))
        
        train_ds = TensorDataset(torch.tensor(X_train_np), torch.tensor(y_train_np))
        test_ds = TensorDataset(torch.tensor(X_test_np), torch.tensor(y_test_np))
        
        train_loader = DataLoader(train_ds, batch_size=256, sampler=sampler)
        test_loader = DataLoader(test_ds, batch_size=512, shuffle=False)
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        log(f"PyTorch training device: {device}")
        
        mlp_model = FraudMLP(X_train_np.shape[1]).to(device)
        criterion = FocalLoss(alpha=0.25, gamma=2.0)
        optimizer = torch.optim.AdamW(mlp_model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
        
        best_auc = 0.0
        best_state = None
        
        epochs = 100
        for epoch in range(1, epochs + 1):
            mlp_model.train()
            for Xb, yb in train_loader:
                Xb, yb = Xb.to(device), yb.to(device)
                optimizer.zero_grad()
                out = mlp_model(Xb)
                loss = criterion(out, yb)
                loss.backward()
                optimizer.step()
            scheduler.step()
            
            if epoch % 10 == 0 or epoch == 1:
                mlp_model.eval()
                all_probs = []
                with torch.no_grad():
                    for Xb, _ in test_loader:
                        prob = torch.sigmoid(mlp_model(Xb.to(device))).cpu().numpy()
                        all_probs.extend(prob)
                auc = roc_auc_score(y_test_np, all_probs)
                if auc > best_auc:
                    best_auc = auc
                    best_state = mlp_model.state_dict().copy()
                log(f"  Epoch {epoch:3d}/{epochs} | Loss: {loss.item():.4f} | Val AUC: {auc:.4f}")
                
        if best_state is not None:
            mlp_model.load_state_dict(best_state)
            
        # Save PyTorch raw weights
        pt_path = os.path.join(output_dir, "best_mlp.pt")
        torch.save(mlp_model.state_dict(), pt_path)
        
        # Save pickleable wrapper
        wrapper = MLPWrapper(mlp_model, device)
        model_path = os.path.join(output_dir, "model_mlp.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(wrapper, f)
            
        y_prob = wrapper.predict_proba(X_test_np)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)
        
        f1 = f1_score(y_test_np, y_pred)
        prec = precision_score(y_test_np, y_pred, zero_division=0)
        rec = recall_score(y_test_np, y_pred, zero_division=0)
        auc = roc_auc_score(y_test_np, y_prob)
        
        log(f"MLP Test Metrics -> F1: {f1:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | ROC-AUC: {auc:.4f}")
        
        metrics["mlp"] = {"F1": f1, "Precision": prec, "Recall": rec, "ROC-AUC": auc}

    # ── 7. VOTING ENSEMBLE ──
    if model_name == "ensemble" or model_name == "all":
        log("--- Notebook 7: Voting Ensemble ---")
        models = {}
        model_names = ['xgboost', 'lightgbm', 'randomforest', 'isoforest', 'mlp']
        
        for name in model_names:
            path = os.path.join(output_dir, f"model_{name}.pkl")
            if os.path.exists(path):
                with open(path, "rb") as f:
                    models[name] = pickle.load(f)
                log(f"Loaded base model: {name}")
            else:
                log(f"Base model {name} not found! Cannot train ensemble.")
                return metrics
                
        # Calibrate Isolation Forest min/max scores on test data to avoid single-record division-by-zero crashes
        if 'isoforest' in models:
            iso_mdl = models['isoforest']
            # Get sample scores to find min/max
            raw_scores = -iso_mdl.score_samples(X_train)
            iso_min = float(raw_scores.min())
            iso_max = float(raw_scores.max())
            log(f"Calibrated Isolation Forest bounds: min={iso_min:.4f}, max={iso_max:.4f}")
        else:
            iso_min, iso_max = 0.0, 1.0
            
        weights = {
            'xgboost': 0.30, 
            'lightgbm': 0.30,
            'randomforest': 0.20, 
            'mlp': 0.15, 
            'isoforest': 0.05
        }
        
        ensemble = EnsembleModel(models, weights, iso_min=iso_min, iso_max=iso_max)
        
        # Test predictions
        ensemble_prob = ensemble.predict_proba_from_X(X_test.values)
        y_pred = (ensemble_prob >= 0.5).astype(int)
        
        f1 = f1_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, ensemble_prob)
        
        log(f"ENSEMBLE Test Metrics -> F1: {f1:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | ROC-AUC: {auc:.4f}")
        
        ensemble_path = os.path.join(output_dir, "model_ensemble.pkl")
        with open(ensemble_path, "wb") as f:
            pickle.dump(ensemble, f)
            
        metrics["ensemble"] = {"F1": f1, "Precision": prec, "Recall": rec, "ROC-AUC": auc}
        
    return metrics

def load_model(model_name: str, model_dir: str):
    """
    Loads and returns the specified pickled model file.
    """
    file_name = f"model_{model_name}.pkl"
    if model_name == "scaler":
        file_name = "scaler.pkl"
    elif model_name == "selected_features":
        file_name = "selected_features.pkl"
        
    model_path = os.path.join(model_dir, file_name)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file {model_path} not found.")
        
    with open(model_path, "rb") as f:
        return pickle.load(f)

def predict(model, feature_dict: dict, scaler=None, selected_features=None) -> dict:
    """
    Takes a loaded model and raw feature dictionary, processes features, scales them,
    and returns fraud probability + label.
    """
    # Load default scaler/features if not provided
    root = Path(__file__).resolve().parents[2]
    model_dir = str(root / "models" / "boi_fraud")
    
    if scaler is None:
        try:
            scaler = load_model("scaler", model_dir)
        except Exception:
            raise FileNotFoundError("Scaler pkl could not be located. Train models first.")
            
    if selected_features is None:
        try:
            selected_features = load_model("selected_features", model_dir)
        except Exception:
            raise FileNotFoundError("Selected features pkl could not be located. Train models first.")

    # Create dataframe for the single dictionary
    df = pd.DataFrame([feature_dict])
    
    # Load categorical mappings if they exist to handle any string features
    try:
        mappings_path = os.path.join(model_dir, "categorical_mappings.pkl")
        if os.path.exists(mappings_path):
            with open(mappings_path, "rb") as f:
                categorical_mappings = pickle.load(f)
            for col, uniques in categorical_mappings.items():
                if col in df.columns:
                    val = df[col].iloc[0]
                    if pd.isna(val):
                        df[col] = np.nan
                    else:
                        try:
                            df[col] = float(uniques.index(val))
                        except ValueError:
                            df[col] = -1.0
    except Exception:
        pass

    # Sanitize incoming feature dictionary column names to align with training columns
    df = df.rename(columns=lambda x: re.sub(r'[\[\]<>,":\{\}\s]', '_', x))

    # Align columns to selected features
    df = df.reindex(columns=selected_features, fill_value=0)
    X_scaled = scaler.transform(df)

    # Detect model type and fetch probabilities
    if hasattr(model, 'predict_proba_from_X'):
        prob = float(model.predict_proba_from_X(X_scaled.astype(np.float32))[0])
    elif hasattr(model, 'predict_proba'):
        prob = float(model.predict_proba(X_scaled.astype(np.float32))[0, 1])
    else:
        # Fallback to decision bounds or raw score
        if hasattr(model, 'score_samples'):
            # Isolation forest
            raw = -model.score_samples(X_scaled)[0]
            # Standard sigmoid mapping as heuristic fallback outside ensemble
            prob = 1.0 / (1.0 + np.exp(-10.0 * (raw - 0.5)))
        else:
            prob = float(model.predict(X_scaled)[0])
            
    label = "FRAUD" if prob >= 0.5 else "LEGIT"
    return {
        "fraud_probability": round(prob, 4),
        "risk_label": label,
        "risk_score": round(prob * 100, 1)
    }
