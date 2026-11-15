"""Alert-budget engine.

Check-in is sent when  P(scam) * V(delay) >= c0 * (1 + alpha * n_recent)
V decays exponentially with minutes-since-payment latency. Tiered responses,
cooldown per user, one check-in per campaign per window.
"""
from __future__ import annotations

import math
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .features import load_features
from .model import temporal_split, score_frame

TIERS = ["silent_log", "soft_checkin", "direct_checkin", "human_callback"]


@dataclass
class BudgetParams:
    c0: float = 0.30
    alpha: float = 0.6
    window_minutes: int = 1440  # 24h recent-count window
    decay: float = 0.05         # lambda; V = exp(-decay * latency_minutes)
    latency_minutes: float = 3.0
    cooldown_minutes: int = 180
    max_checkins_per_user_per_campaign: int = 1

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BudgetParams":
        p = cls()
        for k in ("c0", "alpha", "decay", "latency_minutes"):
            if k in d and d[k] is not None:
                setattr(p, k, float(d[k]))
        for k in ("window_minutes", "cooldown_minutes", "max_checkins_per_user_per_campaign"):
            if k in d and d[k] is not None:
                setattr(p, k, int(d[k]))
        return p


def value_of_delay(latency_minutes: float, decay: float) -> float:
    return math.exp(-decay * latency_minutes)


def _replay(df_test: pd.DataFrame, probs: np.ndarray, params: BudgetParams,
            c0_override: float | None = None) -> dict[str, Any]:
    c0 = c0_override if c0_override is not None else params.c0
    v = value_of_delay(params.latency_minutes, params.decay)
    user_checkins: dict[int, deque[pd.Timestamp]] = defaultdict(deque)
    campaign_count: dict[tuple[int, str], int] = defaultdict(int)
    sent = 0
    caught = 0
    total_scams = int(df_test["label"].sum())
    tier_counts = {t: 0 for t in TIERS}
    checkins_per_day: dict[str, int] = defaultdict(int)

    order = np.argsort(df_test["ts"].to_numpy())
    ids = df_test.index.to_numpy()
    p_arr = probs
    lab = df_test["label"].to_numpy()
    users = df_test["user_id"].to_numpy()
    scam_types = df_test["scam_type"].fillna("legit").to_numpy()
    ts_arr = pd.to_datetime(df_test["ts"]).to_numpy()

    for pos in order:
        u = int(users[pos])
        now = pd.Timestamp(ts_arr[pos])
        dq = user_checkins[u]
        while dq and (now - dq[0]).total_seconds() > params.window_minutes * 60:
            dq.popleft()
        n_recent = len(dq)
        p = float(p_arr[pos])
        threshold = c0 * (1.0 + params.alpha * n_recent)
        budget_ok = p * v >= threshold
        # cooldown
        if dq and (now - dq[-1]).total_seconds() < params.cooldown_minutes * 60:
            budget_ok = False
        # campaign dedup
        campaign = str(scam_types[pos])
        if campaign_count[(u, campaign)] >= params.max_checkins_per_user_per_campaign:
            budget_ok = False

        if not budget_ok:
            tier = "silent_log"
        else:
            ratio = (p * v) / max(threshold, 1e-9)
            if ratio >= 3.0:
                tier = "human_callback"
            elif ratio >= 1.6:
                tier = "direct_checkin"
            else:
                tier = "soft_checkin"
            dq.append(now)
            campaign_count[(u, campaign)] += 1
            sent += 1
            checkins_per_day[str(now.date())] += 1
            if lab[pos] == 1:
                caught += 1
        tier_counts[tier] += 1

    n = len(df_test)
    return {
        "payments": int(n),
        "scams": total_scams,
        "checkins_sent": int(sent),
        "checkins_per_1000": round(sent / max(n, 1) * 1000, 2),
        "recall": round(caught / total_scams, 4) if total_scams else 0.0,
        "tier_counts": tier_counts,
        "c0": float(c0),
        "value_of_delay": round(v, 4),
    }


def simulate(conn: sqlite3.Connection, params: BudgetParams | None = None) -> dict[str, Any]:
    params = params or BudgetParams()
    df = load_features(conn)
    _tr, _cal, test = temporal_split(df)
    probs = score_frame(test)

    operating = _replay(test, probs, params)

    curve = []
    for mult in np.logspace(1.15, -1.15, 16):
        curve.append(_replay(test, probs, params, c0_override=params.c0 * float(mult)))
    curve = sorted(curve, key=lambda d: d["checkins_per_1000"])

    # Fixed-threshold baseline: flag if score >= t, same chronological replay
    baseline = []
    lab = test["label"].to_numpy()
    total_scams = int(lab.sum())
    n = len(test)
    for t in [0.95, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]:
        flagged = probs >= t
        sent = int(flagged.sum())
        recall = float(lab[flagged].sum()) / total_scams if total_scams else 0.0
        baseline.append({"threshold": t, "checkins_per_1000": round(sent / n * 1000, 2),
                         "recall": round(recall, 4), "checkins_sent": sent})
    baseline = sorted(baseline, key=lambda d: d["checkins_per_1000"])

    return {
        "parameters": {
            "c0": params.c0, "alpha": params.alpha, "window_minutes": params.window_minutes,
            "decay": params.decay, "latency_minutes": params.latency_minutes,
            "cooldown_minutes": params.cooldown_minutes,
        },
        "operating_point": operating,
        "curve": [{"checkins_per_1000": d["checkins_per_1000"], "recall": d["recall"], "c0": d["c0"]} for d in curve],
        "baseline_curve": baseline,
        "test_window": {"start": str(pd.to_datetime(test["ts"]).min()), "end": str(pd.to_datetime(test["ts"]).max()),
                        "payments": int(len(test)), "scams": total_scams},
    }
