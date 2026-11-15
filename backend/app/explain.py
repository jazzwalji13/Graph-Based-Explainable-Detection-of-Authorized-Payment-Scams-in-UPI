"""Explainability: reason codes and case-graph JSON for a flagged case."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

import pandas as pd

from .features import FEATURE_COLUMNS

FRIENDLY = {
    "new_payee": "New payee for this customer",
    "amount_z": "Amount far above customer's usual pattern",
    "first_high_value": "First transfer of this size for this customer",
    "hour_of_day": "Time-of-day anomaly",
    "is_unusual_hour": "Payment outside customer's usual hours",
    "call_active": "Call in progress during payment",
    "app_switches": "Rapid app switching during payment",
    "hesitation_secs": "Unusually fast confirmation (pressure indicator)",
    "post_balance_checks": "Repeated balance checks right after paying",
    "post_reversal_search": "Searched for reversal help right after paying",
    "post_support_contact": "Contacted support after paying",
    "post_payee_contact_failed": "Payee unreachable after payment",
    "fd_break": "Fixed deposit broken before payment",
    "loan_taken": "Instant loan taken before payment",
    "payee_prior_reports": "Payee flagged in prior reports",
    "payee_fan_in": "Payee received money from many customers",
    "urgency_score": "Urgency language in call/message",
    "authority_score": "Authority impersonation language",
    "threat_score": "Threat language detected",
    "text_risk": "High-risk script language overall",
    "template_match": "Script matches a known scam template",
    "stage_count": "Full scam stage sequence observed",
}


def _contrib_map(df_row: pd.Series) -> dict[str, float]:
    from .model import raw_contribs  # local import to avoid cycle
    contribs = raw_contribs(pd.DataFrame([df_row]))[0]
    return {c: float(contribs[i]) for i, c in enumerate(FEATURE_COLUMNS)}


def case_reasons(row: pd.Series, prob: float) -> list[str]:
    reasons: list[str] = []
    if row.get("new_payee", 0) >= 1 and row.get("call_active", 0) >= 1:
        reasons.append("New payee + active call + payment under time pressure")
    if row.get("amount_z", 0) >= 2.0:
        reasons.append(f"Amount is {row['amount_z']:.1f}σ above this customer's usual spend")
    if row.get("first_high_value", 0) >= 1:
        reasons.append("First high-value transfer of this size")
    if row.get("fd_break", 0) >= 1:
        reasons.append("Fixed deposit broken shortly before the payment")
    if row.get("loan_taken", 0) >= 1:
        reasons.append("Instant loan disbursed shortly before the payment")
    if row.get("post_reversal_search", 0) >= 1:
        reasons.append("Customer searched for how to reverse a UPI payment")
    if row.get("post_support_contact", 0) >= 1:
        reasons.append("Customer contacted support / 1930 right after paying")
    if row.get("post_payee_contact_failed", 0) >= 1:
        reasons.append("Payee unreachable after the payment")
    if row.get("post_balance_checks", 0) >= 2:
        reasons.append(f"Repeated balance checks ({int(row['post_balance_checks'])}x) in minutes after paying")
    if row.get("payee_prior_reports", 0) >= 2:
        reasons.append(f"Payee flagged in {int(row['payee_prior_reports'])} prior reports")
    if row.get("payee_fan_in", 0) >= 3:
        reasons.append(f"Payee received payments from {int(row['payee_fan_in'])} own customers in this window")
    if row.get("template_match", 0) >= 0.5:
        reasons.append("Script closely matches a known scam template")
    if row.get("authority_score", 0) >= 0.4 or row.get("threat_score", 0) >= 0.4:
        reasons.append("Call/message used authority + threat language (arrest, warrant, fine)")
    if row.get("urgency_score", 0) >= 0.4:
        reasons.append("Strong urgency cues ('immediately', 'within minutes')")
    if row.get("is_unusual_hour", 0) >= 1:
        reasons.append("Payment made outside the customer's usual hours")
    if not reasons:
        top = sorted(FRIENDLY, key=lambda c: -abs(row.get(c, 0) or 0))[:2]
        reasons = [FRIENDLY[c] for c in top]
    return reasons[:5]


_BUCKET = {
    "payment": ["amount_z", "first_high_value", "hour_of_day", "is_unusual_hour", "hesitation_secs", "app_switches"],
    "payee": ["new_payee", "payee_prior_reports", "payee_fan_in"],
    "contact": ["call_active", "urgency_score", "authority_score", "threat_score", "text_risk", "template_match", "stage_count"],
    "mobilization": ["fd_break", "loan_taken"],
    "behavior": ["post_balance_checks", "post_reversal_search", "post_support_contact", "post_payee_contact_failed"],
}

STAGE_CONTRIB_FEATURE = {
    "contact": ["call_active"],
    "authority_claim": ["authority_score"],
    "urgency": ["urgency_score", "threat_score"],
    "payment_request": ["text_risk", "template_match", "stage_count"],
    "follow_up": ["post_balance_checks"],
}


def build_case_graph(conn: sqlite3.Connection, case_id: int) -> dict[str, Any]:
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        raise KeyError(f"case {case_id} not found")
    df_row_df = pd.read_sql_query(
        """SELECT f.*, p.ts, p.day_index, p.amount, p.scam_type, p.hard_negative, p.hard_negative_kind,
                  p.user_id, p.is_demo, p.payee_id
           FROM payment_features f JOIN payments p ON p.id = f.payment_id WHERE f.payment_id = ?""",
        conn, params=(case["payment_id"],),
    )
    if df_row_df.empty:
        raise KeyError("features missing for case payment")
    row = df_row_df.iloc[0]
    contribs = _contrib_map(row)
    pay_ts = str(row["ts"])
    payment_ref = f"UTR-{int(row['payment_id']) * 7351 + 100000:012d}"[-12:]

    events = [dict(r) for r in conn.execute(
        "SELECT stage, ts, channel, lang, text FROM scam_events WHERE payment_id = ? ORDER BY ts", (case["payment_id"],))]
    behaviors = [dict(r) for r in conn.execute(
        "SELECT kind, ts, detail FROM behavior_events WHERE payment_id = ? ORDER BY ts", (case["payment_id"],))]

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    nid = 0

    def add_node(ntype: str, label: str, ts: str, contribution: float, stage: str | None = None) -> str:
        nonlocal nid
        nid += 1
        node = {"id": f"n{nid}", "type": ntype, "label": label, "timestamp": ts,
                "contribution": round(float(contribution), 4)}
        if stage:
            node["stage"] = stage
        nodes.append(node)
        return node["id"]

    def bucket_sum(keys: list[str]) -> float:
        return sum(contribs.get(k, 0.0) for k in keys)

    contact_id = None
    if events:
        stage_counter: dict[str, int] = {}
        for ev in events:
            feats = STAGE_CONTRIB_FEATURE.get(ev["stage"], [])
            contrib = sum(contribs.get(f, 0.0) for f in feats)
            if ev["stage"] == "payment":
                contrib = bucket_sum(_BUCKET["payment"]) + bucket_sum(_BUCKET["payee"])
                continue  # payment node added once below
            label = {
                "contact": f"Contact via {ev['channel'].replace('_', ' ')}",
                "authority_claim": "Claimed authority",
                "urgency": "Urgency pressure",
                "payment_request": "Payment requested",
                "follow_up": "Follow-up after payment",
            }.get(ev["stage"], ev["stage"])
            nid_added = add_node("stage" if ev["stage"] in ("authority_claim", "urgency", "payment_request") else "event",
                                 label, ev["ts"], contrib, stage=ev["stage"])
            stage_counter[ev["stage"]] = nid_added
        contact_id = stage_counter.get("contact")

    pay_label = f"Payment ₹{row['amount']:,.0f} → payee #{int(row['payee_id'])}"
    pay_contrib = bucket_sum(_BUCKET["payment"]) + bucket_sum(_BUCKET["payee"])
    payment_node = add_node("payment", pay_label, pay_ts, pay_contrib)

    if not events:
        # No scam script on record (legit-style flag): surface feature-driven evidence nodes.
        if row.get("call_active", 0) >= 1:
            add_node("event", "Call in progress during payment", pay_ts, contribs.get("call_active", 0.0))
        if row.get("new_payee", 0) >= 1:
            add_node("event", "First-time payee", pay_ts, contribs.get("new_payee", 0.0))
        if row.get("fd_break", 0) >= 1:
            add_node("behavior", "Fixed deposit broken before payment", pay_ts, contribs.get("fd_break", 0.0))
        if row.get("loan_taken", 0) >= 1:
            add_node("behavior", "Instant loan taken before payment", pay_ts, contribs.get("loan_taken", 0.0))

    for b in behaviors:
        kind = b["kind"]
        feat = {"balance_check": "post_balance_checks", "reversal_search": "post_reversal_search",
                "support_contact": "post_support_contact", "payee_contact_failed": "post_payee_contact_failed",
                "fd_break": "fd_break", "loan_taken": "loan_taken"}.get(kind, "text_risk")
        label = {"balance_check": "Balance checked", "reversal_search": "Reversal search",
                 "support_contact": "Contacted support / 1930", "payee_contact_failed": "Payee unreachable",
                 "fd_break": "Fixed deposit broken", "loan_taken": "Instant loan taken"}.get(kind, kind)
        if not events and kind in ("fd_break", "loan_taken"):
            continue  # already added above
        add_node("behavior", label, b["ts"], contribs.get(feat, 0.0))

    # order nodes by timestamp for edges
    ordered = sorted(nodes, key=lambda n: n["timestamp"])
    for a, b in zip(ordered, ordered[1:]):
        edges.append({"source": a["id"], "target": b["id"], "type": "time_order"})
    for n in nodes:
        if n.get("stage") in ("authority_claim", "urgency", "payment_request"):
            edges.append({"source": n["id"], "target": payment_node, "type": "supports_stage"})
        elif n["type"] == "behavior":
            edges.append({"source": n["id"], "target": payment_node, "type": "supports_stage"})

    top_contribs = sorted(((abs(v), k, v) for k, v in contribs.items()), reverse=True)[:6]
    top_sum = sum(abs(v) for _, _, v in top_contribs) or 1.0
    highlight_n = 3
    nodes_by_contrib = sorted(nodes, key=lambda n: -abs(n["contribution"]))
    highlight_ids = {n["id"] for n in nodes_by_contrib[:highlight_n]}
    for n in nodes:
        n["highlighted"] = n["id"] in highlight_ids
        n["contribution_share"] = round(abs(n["contribution"]) / (sum(abs(m["contribution"]) for m in nodes) or 1.0), 4)

    return {
        "case_id": case_id,
        "confidence": float(case["score"]),
        "payment_ref": f"UTR-{payment_ref}",
        "nodes": nodes,
        "edges": edges,
        "top_features": [{"feature": k, "contribution": round(v, 4), "share": round(abs(v) / top_sum, 4)}
                         for _, k, v in top_contribs],
        "reasons": json.loads(case["reasons"]),
    }
