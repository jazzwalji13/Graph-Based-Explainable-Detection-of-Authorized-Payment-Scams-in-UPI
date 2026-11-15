"""Feature extraction from raw tables into payment_features."""
from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np
import pandas as pd

from .simulator import text_risk_scores

FEATURE_COLUMNS = [
    "new_payee", "amount_z", "first_high_value", "hour_of_day", "is_unusual_hour",
    "call_active", "app_switches", "hesitation_secs",
    "post_balance_checks", "post_reversal_search", "post_support_contact", "post_payee_contact_failed",
    "fd_break", "loan_taken",
    "payee_prior_reports", "payee_fan_in",
    "urgency_score", "authority_score", "threat_score", "text_risk",
    "template_match", "stage_count",
]

CONTEXT_ONLY = ["new_payee", "amount_z", "first_high_value", "hour_of_day", "is_unusual_hour",
                "call_active", "app_switches", "hesitation_secs", "payee_prior_reports", "payee_fan_in"]


def build_frame(conn: sqlite3.Connection) -> pd.DataFrame:
    payments = pd.read_sql_query(
        """SELECT p.id AS payment_id, p.user_id, p.payee_id, p.ts, p.day_index, p.amount, p.call_active,
                  p.app_switches, p.hesitation_secs, p.is_new_payee, p.is_scam, p.scam_type, p.hard_negative, p.hard_negative_kind,
                  u.avg_amount, u.amount_stddev, u.hour_start, u.hour_end,
                  py.prior_reports AS payee_prior_reports, py.fan_in AS payee_fan_in
           FROM payments p JOIN users u ON u.id = p.user_id JOIN payees py ON py.id = p.payee_id""",
        conn,
    )
    behavior = pd.read_sql_query("SELECT payment_id, kind, ts FROM behavior_events", conn)
    events = pd.read_sql_query("SELECT payment_id, stage, text FROM scam_events", conn)

    df = payments.copy()
    df["hour_of_day"] = pd.to_datetime(df["ts"]).dt.hour
    df["amount_z"] = ((df["amount"] - df["avg_amount"]) / df["amount_stddev"].clip(lower=1)).clip(-5, 12)
    high = df.groupby("user_id")["amount"].transform(lambda s: s.quantile(0.98))
    df["first_high_value"] = ((df["amount"] > high) & (df["amount"] > 2.5 * df["avg_amount"])).astype(float)
    df["is_unusual_hour"] = ((df["hour_of_day"] < df["hour_start"]) | (df["hour_of_day"] > df["hour_end"])).astype(float)
    df["new_payee"] = df["is_new_payee"].astype(float)
    df["call_active"] = df["call_active"].astype(float)

    # post-payment behavior (events occurring after payment)
    df = df.set_index("payment_id")
    pay_ts = pd.to_datetime(df["ts"])
    if not behavior.empty:
        b = behavior.copy()
        b["ts_dt"] = pd.to_datetime(b["ts"])
        b = b.merge(pay_ts.rename("payment_ts"), left_on="payment_id", right_index=True, how="left")
        post = b[b["ts_dt"] > b["payment_ts"]]
        pre = b[b["ts_dt"] <= b["payment_ts"]]
        df["post_balance_checks"] = post[post["kind"] == "balance_check"].groupby("payment_id").size().reindex(df.index, fill_value=0)
        for kind, col in [("reversal_search", "post_reversal_search"),
                          ("support_contact", "post_support_contact"),
                          ("payee_contact_failed", "post_payee_contact_failed")]:
            df[col] = post[post["kind"] == kind].groupby("payment_id").size().reindex(df.index, fill_value=0).clip(upper=1)
        df["fd_break"] = pre[pre["kind"] == "fd_break"].groupby("payment_id").size().reindex(df.index, fill_value=0).clip(upper=1)
        df["loan_taken"] = pre[pre["kind"] == "loan_taken"].groupby("payment_id").size().reindex(df.index, fill_value=0).clip(upper=1)
    else:
        for col in ["post_balance_checks", "post_reversal_search", "post_support_contact",
                    "post_payee_contact_failed", "fd_break", "loan_taken"]:
            df[col] = 0

    # text risk (max across the payment's scam-event texts; 0 when unavailable)
    if not events.empty:
        scores: dict[int, tuple[float, float, float]] = {}
        counts: dict[int, int] = {}
        for row in events.itertuples(index=False):
            u, a, t = text_risk_scores(row.text)
            cu, ca, ct = scores.get(row.payment_id, (0.0, 0.0, 0.0))
            scores[row.payment_id] = (max(cu, u), max(ca, a), max(ct, t))
            counts[row.payment_id] = counts.get(row.payment_id, 0) + 1
        df["urgency_score"] = pd.Series({k: v[0] for k, v in scores.items()}).reindex(df.index, fill_value=0.0)
        df["authority_score"] = pd.Series({k: v[1] for k, v in scores.items()}).reindex(df.index, fill_value=0.0)
        df["threat_score"] = pd.Series({k: v[2] for k, v in scores.items()}).reindex(df.index, fill_value=0.0)
        df["stage_count"] = pd.Series(counts).reindex(df.index, fill_value=0)
    else:
        df["urgency_score"] = 0.0
        df["authority_score"] = 0.0
        df["threat_score"] = 0.0
        df["stage_count"] = 0

    # Genuine family/medical urgency: real distress messages carry urgency language too.
    # This is the hardest negative for text features — same surface, no authority/threat claims.
    fam_mask = df["hard_negative_kind"].isin(["medical_emergency", "family_transfer"])
    n_fam = int(fam_mask.sum())
    if n_fam:
        fam_rng = np.random.default_rng(20260711)
        df.loc[fam_mask, "urgency_score"] = fam_rng.uniform(0.35, 0.75, n_fam).round(3)
        df.loc[fam_mask, "authority_score"] = 0.0
        df.loc[fam_mask, "threat_score"] = 0.0

    # Genuine bank fraud calls imitate scam language ("your account will be suspended").
    # This is exactly why customers can't tell real calls from fake ones.
    gen_mask = df["hard_negative_kind"] == "genuine_bank_call"
    n_gen = int(gen_mask.sum())
    if n_gen:
        gen_rng = np.random.default_rng(20260712)
        df.loc[gen_mask, "authority_score"] = gen_rng.uniform(0.3, 0.8, n_gen).round(3)
        df.loc[gen_mask, "threat_score"] = gen_rng.uniform(0.1, 0.5, n_gen).round(3)
        df.loc[gen_mask, "urgency_score"] = gen_rng.uniform(0.2, 0.6, n_gen).round(3)

    df["text_risk"] = (0.4 * df["urgency_score"] + 0.35 * df["authority_score"] + 0.25 * df["threat_score"]).clip(0, 1)

    # stage_count: funnel stages observed from text; when text is missing, derive a noisy
    # 0-4 "distress funnel" from post-payment behaviour (overlaps with legit emergencies).
    derived = ((df["post_balance_checks"] >= 2).astype(int) + df["post_reversal_search"]
               + df["post_support_contact"] + df["post_payee_contact_failed"]).clip(upper=4)
    df["stage_count"] = np.where(df["stage_count"] > 0, df["stage_count"], derived)

    df["template_match"] = 0.0  # filled by discovery.py after clustering
    df = df.reset_index()
    df["label"] = df["is_scam"].astype(int)
    return df


def store_features(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    rows = []
    for r in df.itertuples(index=False):
        rows.append((
            int(r.payment_id), float(r.new_payee), float(r.amount_z), float(r.first_high_value),
            float(r.hour_of_day), float(r.is_unusual_hour), float(r.call_active), float(r.app_switches),
            float(r.hesitation_secs), float(r.post_balance_checks), float(r.post_reversal_search),
            float(r.post_support_contact), float(r.post_payee_contact_failed), float(r.fd_break),
            float(r.loan_taken), float(r.payee_prior_reports), float(r.payee_fan_in),
            float(r.urgency_score), float(r.authority_score), float(r.threat_score), float(r.text_risk),
            float(r.template_match), float(r.stage_count), int(r.label),
        ))
    conn.execute("DELETE FROM payment_features")
    conn.executemany(
        """INSERT INTO payment_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()


def load_features(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT f.*, p.ts, p.day_index, p.amount, p.scam_type, p.hard_negative, p.hard_negative_kind, p.user_id, p.is_demo "
        "FROM payment_features f JOIN payments p ON p.id = f.payment_id ORDER BY p.ts",
        conn, parse_dates=["ts"],
    )


def feature_vector(row: dict[str, Any]) -> list[float]:
    return [float(row[c]) for c in FEATURE_COLUMNS]
