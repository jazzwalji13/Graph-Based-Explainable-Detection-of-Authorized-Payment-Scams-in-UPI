"""Structured report builder. Template fallback by default; optional LLM phrasing only."""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.request
import uuid
from datetime import datetime
from typing import Any

from .simulator import SCAM_TYPES

COMPLETENESS_WEIGHTS = {
    "payment_refs": 0.08, "amount": 0.08, "payee": 0.08, "scam_type": 0.08,
    "stage_timeline": 0.14, "first_contact_channel": 0.07, "claimed_identity": 0.07,
    "urgency_cues": 0.05, "communication_identifiers": 0.09, "evidence": 0.07,
    "model_reasons": 0.08, "customer_confirmation": 0.07, "consent": 0.04,
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _events(conn: sqlite3.Connection, payment_id: int) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(
        "SELECT stage, ts, channel, lang, text FROM scam_events WHERE payment_id = ? ORDER BY ts", (payment_id,))]


def _behaviors(conn: sqlite3.Connection, payment_id: int) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(
        "SELECT kind, ts, detail FROM behavior_events WHERE payment_id = ? ORDER BY ts", (payment_id,))]


def build_payload(conn: sqlite3.Connection, case_id: int) -> dict[str, Any]:
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        raise KeyError(f"case {case_id} not found")
    pay = conn.execute(
        """SELECT p.*, u.name AS user_name, u.city, py.handle AS payee_handle, py.name AS payee_name,
                  py.prior_reports AS payee_prior_reports
           FROM payments p JOIN users u ON u.id = p.user_id JOIN payees py ON py.id = p.payee_id
           WHERE p.id = ?""", (case["payment_id"],)).fetchone()
    events = _events(conn, case["payment_id"])
    behaviors = _behaviors(conn, case["payment_id"])
    reasons = json.loads(case["reasons"])

    scam_type = pay["scam_type"] or "unknown"
    type_label = SCAM_TYPES.get(scam_type, {}).get("label", scam_type)
    stage_timeline = [{"stage": e["stage"], "ts": e["ts"], "detail": e["text"]} for e in events]
    first_contact = events[0] if events else None
    urgency_cues = []
    for e in events:
        for w in ["immediately", "within", "urgent", "turant", "jaldi", "abhi", "तुरंत", "अभी", "minutes"]:
            if w in e["text"].lower() and w not in urgency_cues:
                urgency_cues.append(w)
    contact_channel = first_contact["channel"] if first_contact else ("voice_call" if pay["call_active"] else "unknown")

    checkins = [dict(r) for r in conn.execute(
        "SELECT sent_at, tier, answer, answered_at FROM checkins WHERE case_id = ? ORDER BY id", (case_id,))]
    confirmation = "confirmed_scam" if case["status"] == "confirmed" else (
        "denied_legit" if case["status"] == "denied" else (
            "unsure" if case["status"] == "unsure" else "pending"))

    payment_ref = f"UTR{int(pay['id']) * 7351 + 918273:012d}"[-12:]
    payload = {
        "report_id": uuid.uuid4().hex[:12].upper(),
        "created_at": _now(),
        "timestamps": {
            "first_contact": first_contact["ts"] if first_contact else None,
            "payment": pay["ts"],
            "customer_confirmation": case["answered_at"],
            "report_created": _now(),
        },
        "payment_refs": {"utr": f"UTR-{payment_ref}", "upi_ref": f"UPI{int(pay['id']) * 9917 + 55231:010d}"},
        "amount": pay["amount"],
        "currency": "INR",
        "payee": {
            "identifier": f"UPI-{int(pay['payee_id']):08d}",
            "handle": pay["payee_handle"],
            "name": pay["payee_name"],
            "prior_reports": pay["payee_prior_reports"],
        },
        "scam_type": scam_type,
        "scam_type_label": type_label,
        "stage_timeline": stage_timeline,
        "first_contact_channel": contact_channel,
        "claimed_identity": SCAM_TYPES.get(scam_type, {}).get("identity", "Not captured"),
        "urgency_cues": urgency_cues or ["time pressure implied"],
        "communication_identifiers": {
            "caller_number_masked": "+91-98XXX-" + str((int(pay["id"]) * 37) % 100000).zfill(5),
            "payee_handle": pay["payee_handle"],
            "languages": sorted({e["lang"] for e in events}) or ["hinglish"],
        },
        "evidence": [
            {"name": "call_recording_snippet.mp3", "kind": "audio", "mock": True},
            {"name": "sms_screenshot.png", "kind": "image", "mock": True},
            {"name": "stage_timeline.json", "kind": "json", "mock": True},
        ],
        "model": {"confidence": case["score"], "risk_tier": case["risk_tier"], "reason_codes": reasons},
        "customer_confirmation": {
            "status": confirmation,
            "checkins": checkins,
            "answer_note": "Customer confirmed under non-accusatory check-in wording.",
        },
        "consent": {"share_with_bank": True, "share_with_ncrb_portal": True, "anonymous_analytics": True},
        "synthetic_data_notice": "SYNTHETIC — generated for demonstration. Not a real incident.",
    }
    payload["completeness"] = completeness_score(payload)
    payload["narrative"], payload["llm_used"] = render_narrative(payload)
    return payload


def completeness_score(payload: dict[str, Any]) -> float:
    checks = {
        "payment_refs": bool(payload.get("payment_refs", {}).get("utr")),
        "amount": bool(payload.get("amount")),
        "payee": bool(payload.get("payee", {}).get("handle")),
        "scam_type": payload.get("scam_type") not in (None, "unknown"),
        "stage_timeline": len(payload.get("stage_timeline", [])) >= 4,
        "first_contact_channel": payload.get("first_contact_channel") not in (None, "unknown"),
        "claimed_identity": payload.get("claimed_identity") not in (None, "Not captured"),
        "urgency_cues": bool(payload.get("urgency_cues")),
        "communication_identifiers": bool(payload.get("communication_identifiers", {}).get("caller_number_masked")),
        "evidence": bool(payload.get("evidence")),
        "model_reasons": bool(payload.get("model", {}).get("reason_codes")),
        "customer_confirmation": payload.get("customer_confirmation", {}).get("status") in
                                 ("confirmed_scam", "denied_legit", "unsure"),
        "consent": all(payload.get("consent", {}).values()),
    }
    return round(sum(w for k, w in COMPLETENESS_WEIGHTS.items() if checks.get(k)) * 100, 1)


def render_narrative(payload: dict[str, Any]) -> tuple[str, bool]:
    llm_key = os.environ.get("LLM_API_KEY")
    facts = {
        "amount": payload["amount"], "scam_type": payload["scam_type_label"],
        "first_contact_channel": payload["first_contact_channel"],
        "claimed_identity": payload["claimed_identity"],
        "stage_count": len(payload["stage_timeline"]),
        "confirmation": payload["customer_confirmation"]["status"],
    }
    if llm_key:
        try:
            body = json.dumps({
                "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content":
                        "You phrase bank fraud-report narratives. Use ONLY the facts in the JSON. "
                        "Never invent names, amounts or identifiers. Two sentences, plain English."},
                    {"role": "user", "content": json.dumps(facts)},
                ],
                "max_tokens": 160, "temperature": 0.2,
            }).encode()
            req = urllib.request.Request(
                os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions"),
                data=body, headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip(), True
        except Exception:
            pass  # fall through to deterministic template
    return (
        f"Customer reported a suspected {facts['scam_type']} contact via {facts['first_contact_channel']}. "
        f"The caller claimed to be {facts['claimed_identity']} and induced a payment of Rs {facts['amount']:,.0f} "
        f"under time pressure. The customer confirmation status is {facts['confirmation']}. "
        f"Stage timeline with {facts['stage_count']} observed stages is attached."
    ), False
