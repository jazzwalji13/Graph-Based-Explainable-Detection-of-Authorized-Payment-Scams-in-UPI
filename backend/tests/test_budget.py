from __future__ import annotations

import math

import numpy as np
import pytest

from app import budget


def test_value_decay_monotonic():
    v0 = budget.value_of_delay(0, decay=0.05)
    v30 = budget.value_of_delay(30, decay=0.05)
    v120 = budget.value_of_delay(120, decay=0.05)
    assert v0 == pytest.approx(1.0)
    assert v0 > v30 > v120 > 0
    assert budget.value_of_delay(60, 0.05) == pytest.approx(math.exp(-3))


def test_budget_params_from_dict():
    p = budget.BudgetParams.from_dict({"c0": 0.5, "alpha": 1.2, "window_minutes": 60, "decay": 0.1,
                                       "cooldown_minutes": 30})
    assert p.c0 == 0.5 and p.alpha == 1.2 and p.window_minutes == 60
    assert p.decay == 0.1 and p.cooldown_minutes == 30
    assert budget.BudgetParams.from_dict({}) == budget.BudgetParams()


def _replay_frame():
    import pandas as pd
    rows = []
    ts = pd.Timestamp("2026-10-01 08:00:00")
    # 40 legit tiny-risk payments, 10 scam-ish high-risk payments
    for i in range(50):
        scam = i >= 40
        rows.append({
            "payment_id": i + 1, "user_id": 1000 + i, "ts": str(ts + pd.Timedelta(minutes=7 * i)),
            "day_index": 0, "amount": 5000 if scam else 300, "label": 1 if scam else 0,
            "scam_type": "utility_bill" if scam else None, "hard_negative": 0,
            "hard_negative_kind": None, "user_id_dup": None,
        })
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"])
    probs = np.array([0.05] * 40 + [0.9] * 10)
    return df, probs


def test_replay_respects_cooldown_and_budget():
    df, probs = _replay_frame()
    p = budget.BudgetParams(c0=0.3, alpha=0.5, window_minutes=1440, decay=0.05,
                            latency_minutes=3, cooldown_minutes=180)
    out = budget._replay(df, probs, p)
    assert out["scams"] == 10
    assert out["checkins_sent"] == 10  # all-high-risk payments check in (unique users)
    assert out["recall"] == pytest.approx(1.0)
    assert out["checkins_per_1000"] == pytest.approx(200.0)
    # higher c0 suppresses everything
    out2 = budget._replay(df, probs, p, c0_override=99.0)
    assert out2["checkins_sent"] == 0
    assert out2["recall"] == 0.0


def test_replay_caps_same_user_campaign():
    df, probs = _replay_frame()
    df["user_id"] = 1  # same user, same campaign (utility_bill for scams)
    df["scam_type"] = "utility_bill"
    p = budget.BudgetParams(c0=0.01, alpha=0.0, window_minutes=100000, decay=0.001,
                            latency_minutes=3, cooldown_minutes=0, max_checkins_per_user_per_campaign=1)
    out = budget._replay(df, probs, p)
    assert out["checkins_sent"] == 1  # deduped to one per campaign
