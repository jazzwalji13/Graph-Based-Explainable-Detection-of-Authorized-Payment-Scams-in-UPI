"""Synthetic evaluation metrics -> data/metrics.json (read by the Metrics page)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
from sklearn.metrics import average_precision_score

from .features import CONTEXT_ONLY, FEATURE_COLUMNS, load_features
from .model import load_model, score_frame, temporal_split

METRICS_PATH = Path(__file__).resolve().parent.parent / "data" / "metrics.json"
FLAG_THRESHOLD = 0.62


def _rule_based(df) -> np.ndarray:
    flag = ((df["new_payee"] >= 1) & (df["call_active"] >= 1) & (df["amount_z"] >= 2.0)).to_numpy()
    return flag.astype(float)


def _txn_only(train, test) -> np.ndarray:
    Xtr, ytr = train[CONTEXT_ONLY], train["label"]
    spw = float(max(1.0, (ytr == 0).sum() / max(1, (ytr == 1).sum())))
    m = lgb.LGBMClassifier(n_estimators=250, learning_rate=0.06, num_leaves=31,
                           scale_pos_weight=spw, random_state=42, verbose=-1)
    m.fit(Xtr, ytr)
    return m.predict_proba(test[CONTEXT_ONLY])[:, 1]


def run(conn: sqlite3.Connection) -> dict[str, Any]:
    df = load_features(conn)
    train, _calib, test = temporal_split(df)
    probs = score_frame(test)
    y = test["label"].to_numpy()

    n = len(test)
    flag = probs >= FLAG_THRESHOLD
    hard_neg = test["hard_negative"].to_numpy() == 1
    budget = max(1, int(0.02 * n))
    top_idx = probs.argsort()[::-1][:budget]

    pr_auc = float(average_precision_score(y, probs))
    rule = _rule_based(test)
    txn_probs = _txn_only(train, test)

    per_type = {}
    for stype in sorted(test["scam_type"].dropna().unique()):
        mask = (test["scam_type"] == stype).to_numpy()
        per_type[str(stype)] = round(float(flag[mask].mean()), 4) if mask.any() else None

    metrics = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "synthetic": True,
        "banner": "Synthetic data. Not real-world performance.",
        "test_window": {"start": str(test["ts"].min()), "end": str(test["ts"].max()),
                        "payments": int(n), "scams": int(y.sum())},
        "flag_threshold": FLAG_THRESHOLD,
        "budget_fraction": 0.02,
        "model": {
            "pr_auc": round(pr_auc, 4),
            "recall_at_flag_threshold": round(float(y[flag].sum() / max(1, y.sum())), 4),
            "recall_at_fixed_budget": round(float(y[top_idx].sum() / max(1, y.sum())), 4),
            "false_flag_rate_hard_negatives": round(float((flag & hard_neg.astype(bool)).sum() / max(1, hard_neg.sum())), 4),
            "checkins_per_1000": round(float(flag.sum() / n * 1000), 2),
            "precision_at_flag_threshold": round(float(y[flag].sum() / max(1, flag.sum())), 4),
            "leave_one_scam_type_out_recall": per_type,
        },
        "baselines": {
            "rule_based": {
                "recall": round(float(y[rule.astype(bool)].sum() / max(1, y.sum())), 4),
                "false_flag_rate_hard_negatives": round(float(((rule == 1) & hard_neg.astype(bool)).sum() / max(1, hard_neg.sum())), 4),
                "checkins_per_1000": round(float(rule.sum() / n * 1000), 2),
            },
            "transaction_only_model": {
                "pr_auc": round(float(average_precision_score(y, txn_probs)), 4),
                "recall_at_fixed_budget": round(float(y[txn_probs.argsort()[::-1][:budget]].sum() / max(1, y.sum())), 4),
                "recall_at_flag_threshold": round(float(y[txn_probs >= FLAG_THRESHOLD].sum() / max(1, y.sum())), 4),
                "checkins_per_1000": round(float((txn_probs >= FLAG_THRESHOLD).sum() / n * 1000), 2),
            },
        },
        "notes": [
            "Temporal split: first 66% train, next 12% calibration, final 22% test.",
            "PR-AUC = average precision on the held-out future window.",
            "Recall@fixed_budget = share of test scams captured by flagging the top 2% of payments by risk.",
            "False-flag rate measured on hard negatives: rent deposits, medical emergencies, genuine bank calls, family transfers, tuition fees.",
        ],
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
