"""LightGBM training with temporal split + sigmoid calibration. Saved via joblib."""
from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV

try:  # scikit-learn >= 1.6
    from sklearn.frozen import FrozenEstimator

    def _fit_calibrator(model, Xcal, ycal):
        cal = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
        cal.fit(Xcal, ycal)
        return cal

except ImportError:  # older scikit-learn: manual Platt scaling on raw margins
    from sklearn.linear_model import LogisticRegression

    class _PlattWrapper:
        def __init__(self, model, lr):
            self.model, self.lr = model, lr

        def predict_proba(self, X):
            margins = self.model.booster_.predict(X, raw_score=True).reshape(-1, 1)
            p1 = self.lr.predict_proba(margins)[:, 1]
            return np.column_stack([1 - p1, p1])

    def _fit_calibrator(model, Xcal, ycal):
        margins = model.booster_.predict(Xcal, raw_score=True).reshape(-1, 1)
        lr = LogisticRegression(C=1.0, solver="lbfgs")
        lr.fit(margins, ycal)
        return _PlattWrapper(model, lr)

from .features import FEATURE_COLUMNS, load_features

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA_DIR / "model.joblib"


def temporal_split(df: pd.DataFrame, train_frac: float = 0.66, calib_frac: float = 0.12):
    df = df.sort_values("ts").reset_index(drop=True)
    n = len(df)
    t_end = int(n * train_frac)
    c_end = int(n * (train_frac + calib_frac))
    return df.iloc[:t_end], df.iloc[t_end:c_end], df.iloc[c_end:]


def train_and_save(conn: sqlite3.Connection, seed: int = 42) -> dict[str, Any]:
    df = load_features(conn)
    train, calib, _test = temporal_split(df)
    Xtr, ytr = train[FEATURE_COLUMNS], train["label"]
    Xcal, ycal = calib[FEATURE_COLUMNS], calib["label"]
    spw = float(max(1.0, (ytr == 0).sum() / max(1, (ytr == 1).sum())))
    model = lgb.LGBMClassifier(
        n_estimators=450, learning_rate=0.05, num_leaves=48, max_depth=-1,
        subsample=0.85, subsample_freq=1, colsample_bytree=0.85,
        scale_pos_weight=spw, random_state=seed, n_jobs=4, verbose=-1,
    )
    model.fit(Xtr, ytr)
    calibrator = _fit_calibrator(model, Xcal, ycal)
    artifact = {"lgbm": model, "calibrator": calibrator, "features": FEATURE_COLUMNS}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    return {"train_rows": int(len(train)), "calib_rows": int(len(calib)), "scale_pos_weight": spw}


@lru_cache(maxsize=1)
def load_model() -> dict[str, Any]:
    return joblib.load(MODEL_PATH)


def score_frame(df: pd.DataFrame) -> np.ndarray:
    art = load_model()
    X = df[art["features"]]
    return art["calibrator"].predict_proba(X)[:, 1]


def raw_contribs(df: pd.DataFrame) -> np.ndarray:
    """SHAP-style per-feature contributions from the underlying LightGBM booster."""
    art = load_model()
    X = df[art["features"]].to_numpy()
    contribs = art["lgbm"].booster_.predict(X, pred_contrib=True)
    return contribs[:, :-1]  # drop bias term


def flag_cases(conn: sqlite3.Connection, flag_threshold: float) -> int:
    """Create cases for payments scoring above the flag threshold."""
    from .explain import case_reasons  # local import to avoid cycle

    df = load_features(conn)
    df = df.sort_values("ts").reset_index(drop=True)
    probs = score_frame(df)
    flagged = df[probs >= flag_threshold]
    created = 0
    for (_, row), prob in zip(flagged.iterrows(), probs[probs >= flag_threshold]):
        reasons = json.dumps(case_reasons(row, prob))
        tier = "critical" if prob >= 0.85 else ("high" if prob >= 0.75 else "elevated")
        conn.execute(
            """INSERT INTO cases(payment_id, user_id, score, risk_tier, status, reasons, checkin_state, created_at)
               VALUES (?,?,?,?, 'open', ?, 'not_sent', ?)""",
            (int(row["payment_id"]), int(row["user_id"]), float(prob), tier, reasons,
             str(pd.Timestamp.now())),
        )
        created += 1
    conn.commit()
    return created
