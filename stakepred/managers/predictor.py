import os
import datetime
import threading
import time
from collections import deque
from typing import TYPE_CHECKING
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, log_loss, mean_squared_error
import joblib

from ..logger import get_logger

if TYPE_CHECKING:
    from ..models import CrashRound

logger = get_logger("AdvancedPredictor")

# ---------- USER SETTINGS ----------
DATA_CSV = "crash_history.csv"    # persistent dataset
MODEL_CLASS_FILE = "./models/clf_model.joblib"
MODEL_REG_FILE = "./models/reg_model.joblib"
DEFAULT_TARGET_MULTIPLIER = 2.0
HISTORY_WINDOW = 600           # how many recent rounds kept in memory for features
FEATURE_ROUNDS = 20             # how many lags to use for feature vector
MIN_DATA_TO_TRAIN = 150         # require at least this many examples to train
POLL_INTERVAL = 0.5
SMOOTH_THRESHOLD = 0.05
AUTO_TRAIN = True
AUTO_TRAIN_INTERVAL = 600       # seconds (10 min)

# ---------- Helper: feature engineering ----------
def extract_features_from_history(
    history, target=DEFAULT_TARGET_MULTIPLIER, n_lags=FEATURE_ROUNDS,
    alpha=0.3, weight_type="linear"
):
    if len(history) < n_lags:
        return None

    arr = np.array(list(history)[-n_lags:])
    feats = {}

    # --- lag features ---
    for i in range(n_lags):
        feats[f"lag_{i+1}"] = arr[-(i+1)]

    # deltas
    deltas = np.diff(arr)
    feats["delta_mean"] = float(np.mean(deltas))
    feats["delta_std"] = float(np.std(deltas))

    # simple stats
    feats["arr_mean"] = float(np.mean(arr))
    feats["arr_std"] = float(np.std(arr))
    feats["arr_min"] = float(np.min(arr))
    feats["arr_max"] = float(np.max(arr))

    # --- weighted EMA ---
    ema = arr[0]
    for val in arr[1:]:
        ema = alpha * val + (1 - alpha) * ema
    feats["ema"] = float(ema)

    # --- weighted mean/std ---
    if weight_type == "linear":
        weights = np.linspace(1, 2, n_lags)
    elif weight_type == "exponential":
        weights = 2 ** np.linspace(0, n_lags-1, n_lags)  # recent rounds much higher weight
    else:
        weights = np.ones(n_lags)

    feats["weighted_mean"] = float(np.average(arr, weights=weights))
    feats["weighted_std"] = float(np.sqrt(np.average((arr - feats["weighted_mean"])**2, weights=weights)))

    # percentiles
    for p in [10, 25, 50, 75, 90]:
        feats[f"p{p}"] = float(np.percentile(arr, p))

    # count above target, last value relative to target
    feats["count_ge_target"] = int(np.sum(arr >= target))
    feats["last_over_target"] = int(arr[-1] >= target)

    # streaks
    streak_above = streak_below = 0
    for val in arr[::-1]:
        if val >= target and streak_below == 0:
            streak_above += 1
        elif val < target and streak_above == 0:
            streak_below += 1
        else:
            break
    feats["streak_above"] = streak_above
    feats["streak_below"] = streak_below

    # coefficient of variation
    feats["cv"] = float(np.std(arr) / (np.mean(arr) + 1e-8))

    # slope
    x = np.arange(len(arr))
    feats["slope"] = float(np.polyfit(x, arr, 1)[0]) if np.std(x) > 0 else 0.0

    return feats


# ---------- Data manager: save / load rounds ----------
def append_round_to_csv(multiplier, target=DEFAULT_TARGET_MULTIPLIER, csv_path=DATA_CSV):
    """Append a round entry (multiplier, timestamp) to CSV for later training"""
    df = pd.DataFrame([{
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "multiplier": float(multiplier),
        "target": float(target)
    }])
    if not os.path.exists(csv_path):
        df.to_csv(csv_path, index=False)
    else:
        df.to_csv(csv_path, mode='a', header=False, index=False)

# ----------load_dataset_from_csv with this ----------
def load_dataset_from_csv(csv_path=DATA_CSV, n_lags=FEATURE_ROUNDS):
    """Load CSV file and convert to X,y for classification/regression using rolling windows"""
    if not os.path.exists(csv_path):
        return None, None, None, None  # no data
    df = pd.read_csv(csv_path)
    if df.empty:
        return None, None, None, None
    multipliers = df['multiplier'].astype(float).values
    X_rows = []
    y_class = []
    y_reg = []
    feat_names = None
    for i in range(n_lags, len(multipliers)):
        history_window = multipliers[i-n_lags:i]
        target = df['target'].iloc[i]
        feats = extract_features_from_history(history_window, target=target, n_lags=n_lags)
        if feats is None:
            continue
        if feat_names is None:
            feat_names = list(feats.keys())
        X_rows.append(list(feats.values()))
        y_class.append(1 if multipliers[i] >= target else 0)
        y_reg.append(multipliers[i])
    if len(X_rows) == 0:
        return None, None, None, None
    X = np.array(X_rows)
    return X, np.array(y_class), np.array(y_reg), feat_names


# ---------- Advanced Predictor (new) ----------
class AdvancedPredictor:
    def __init__(self, target=DEFAULT_TARGET_MULTIPLIER, n_lags=FEATURE_ROUNDS,
                 alpha=0.3, weight_type="linear"):
        self.target = target
        self.n_lags = n_lags
        self.alpha = alpha
        self.weight_type = weight_type
        self.history = deque(maxlen=HISTORY_WINDOW)
        self.clf_pipeline = None
        self.reg_pipeline = None
        self.feature_names = None
        self.new_rounds_since_train = 0

    def make_feature_vector(self):
        history_values = [v for ts, v in self.history]
        feats = extract_features_from_history(
            history_values,
            target=self.target,
            n_lags=self.n_lags,
            alpha=self.alpha,
            weight_type=self.weight_type
        )
        if feats is None:
            return None, None
        return np.array(list(feats.values())).reshape(1, -1), list(feats.keys())

    def add_round(self, multiplier):
        ts = datetime.datetime.now(datetime.timezone.utc)
        self.history.append((ts, float(multiplier)))
        self.new_rounds_since_train += 1
    
    def auto_train_if_needed(self, min_new=50, csv_path=DATA_CSV):
        """
        Retrain models automatically if at least min_new rounds added since last training
        """
        if self.new_rounds_since_train >= min_new:
            try:
                stats = self.train_models_from_csv(csv_path=csv_path)
                self.save_models()
                self.new_rounds_since_train = 0  # reset counter
                logger.info(f"[AutoTrain] Model retrained on {stats['n_samples']} samples. Accuracy={stats['accuracy']:.3f}")
            except Exception as e:
                logger.error(f"[AutoTrain] Error: {e}")


    def predict_next_multiplier(self):
        vec, names = self.make_feature_vector()
        if vec is None or self.reg_pipeline is None:
            return None
        pred = self.reg_pipeline.predict(vec)[0]
        return float(pred)

    def predict_next_safety(self):
        vec, names = self.make_feature_vector()
        if vec is None or self.clf_pipeline is None:
            return None
        prob = self.clf_pipeline.predict_proba(vec)[0][1]
        return float(prob)

    def risk_label(self, threshold_low=0.45, threshold_high=0.75):
        p = self.predict_next_safety()
        if p is None:
            return "Not enough data"
        if p >= threshold_high:
            return "Low Risk"
        elif p >= threshold_low:
            return "Medium Risk"
        else:
            return "High Risk"



    def train_models_from_csv(self, csv_path=DATA_CSV, min_rows=MIN_DATA_TO_TRAIN):
        # load and prepare dataset
        res = load_dataset_from_csv(csv_path, n_lags=self.n_lags)
        if res is None or res[0] is None:
            raise RuntimeError("Not enough data to build dataset.")
        X, y_class, y_reg, feat_names = res
        if X.shape[0] < min_rows:
            raise RuntimeError(f"Need at least {min_rows} rows, have {X.shape[0]}.")
        self.feature_names = feat_names
        # train-test split
        X_train, X_test, y_class_train, y_class_test, y_reg_train, y_reg_test = train_test_split(
            X, y_class, y_reg, test_size=0.2, random_state=42, stratify=y_class)
        # classification pipeline
        clf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42, n_jobs=-1)
        clf_pipe = Pipeline([('scaler', StandardScaler()), ('clf', clf)])
        clf_pipe.fit(X_train, y_class_train)
        # regression pipeline
        reg = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
        reg_pipe = Pipeline([('scaler', StandardScaler()), ('reg', reg)])
        reg_pipe.fit(X_train, y_reg_train)
        # store
        self.clf_pipeline = clf_pipe
        self.reg_pipeline = reg_pipe
        # evaluation
        y_class_pred = clf_pipe.predict(X_test)
        y_class_prob = clf_pipe.predict_proba(X_test)[:,1]
        y_reg_pred = reg_pipe.predict(X_test)
        acc = accuracy_score(y_class_test, y_class_pred)
        ll = log_loss(y_class_test, np.vstack([1-y_class_prob, y_class_prob]).T)
        mse = mean_squared_error(y_reg_test, y_reg_pred)
        return {"accuracy": acc, "log_loss": ll, "mse": mse, "n_samples": X.shape[0]}

    def save_models(self, clf_path=MODEL_CLASS_FILE, reg_path=MODEL_REG_FILE):
        if self.clf_pipeline is not None:
            joblib.dump(self.clf_pipeline, clf_path)
        if self.reg_pipeline is not None:
            joblib.dump(self.reg_pipeline, reg_path)

    def load_models(self, clf_path=MODEL_CLASS_FILE, reg_path=MODEL_REG_FILE):
        if os.path.exists(clf_path):
            self.clf_pipeline = joblib.load(clf_path)
        if os.path.exists(reg_path):
            self.reg_pipeline = joblib.load(reg_path)
