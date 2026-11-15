"""SCAM-REPORT API. Synthetic data only. Submission is SIMULATED."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import budget, db, discovery, evaluate, explain, model, report, simulator
from .features import FEATURE_COLUMNS
from .schemas import BudgetSimulateRequest, CheckinRequest, SimulateRequest
from .seed import run_pipeline

APP_VERSION = "1.0.0"
app = FastAPI(title="SCAM-REPORT API", version=APP_VERSION,
              description="Bank-agnostic post-payment scam detection & reporting layer. SYNTHETIC DATA.")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)


def get_conn():
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _case_row(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row:
    row = conn.execute(
        """SELECT c.*, p.ts AS payment_ts, p.amount, p.scam_type, p.payee_id, p.is_demo,
                  u.name AS user_name, u.city, u.segment,
                  py.handle AS payee_handle, py.name AS payee_name, py.prior_reports AS payee_prior_reports,
                  py.fan_in AS payee_fan_in
           FROM cases c JOIN payments p ON p.id = c.payment_id
           JOIN users u ON u.id = c.user_id JOIN payees py ON py.id = p.payee_id
           WHERE c.id = ?""", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "case not found")
    return row


def _case_summary_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["reasons"] = json.loads(d.get("reasons") or "[]")
    return d


# ---------- meta ----------

@app.get("/health")
def health(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    seeded = db.get_meta(conn, "seed") is not None
    return {"status": "ok", "version": APP_VERSION, "time": _now(), "seeded": seeded}


@app.post("/simulate")
def simulate(req: SimulateRequest) -> dict[str, Any]:
    overrides = req.model_dump(exclude_none=True)
    summary = run_pipeline(overrides or None)
    return {"ok": True, "summary": summary}


# ---------- cases ----------

@app.get("/cases/summary")
def cases_summary(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    open_c = conn.execute("SELECT COUNT(*) c FROM cases WHERE status = 'open'").fetchone()["c"]
    confirmed = conn.execute("SELECT COUNT(*) c FROM cases WHERE status = 'confirmed'").fetchone()["c"]
    denied = conn.execute("SELECT COUNT(*) c FROM cases WHERE status = 'denied'").fetchone()["c"]
    total = conn.execute("SELECT COUNT(*) c FROM cases").fetchone()["c"]
    row = conn.execute(
        """SELECT AVG((julianday(c.answered_at) - julianday(p.ts)) * 1440) AS mins
           FROM cases c JOIN payments p ON p.id = c.payment_id
           WHERE c.answered_at IS NOT NULL""").fetchone()
    return {
        "open": open_c, "confirmed": confirmed, "denied": denied, "total_flagged": total,
        "avg_minutes_to_confirm": round(row["mins"], 1) if row and row["mins"] else None,
        "synthetic_data": True,
    }


@app.get("/cases")
def list_cases(
    status: Optional[str] = None,
    scam_type: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    q: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    where, params = [], []
    if status:
        where.append("c.status = ?"); params.append(status)
    if scam_type:
        where.append("p.scam_type = ?"); params.append(scam_type)
    if min_score is not None:
        where.append("c.score >= ?"); params.append(min_score)
    if max_score is not None:
        where.append("c.score <= ?"); params.append(max_score)
    if q:
        where.append("(u.name LIKE ? OR py.handle LIKE ?)"); params += [f"%{q}%", f"%{q}%"]
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(
        f"""SELECT COUNT(*) c FROM cases c
            JOIN payments p ON p.id = c.payment_id JOIN users u ON u.id = c.user_id
            JOIN payees py ON py.id = p.payee_id {clause}""", params).fetchone()["c"]
    rows = conn.execute(
        f"""SELECT c.*, p.ts AS payment_ts, p.amount, p.scam_type, p.payee_id, p.is_demo,
                  u.name AS user_name, u.city, u.segment,
                  py.handle AS payee_handle, py.name AS payee_name,
                  py.prior_reports AS payee_prior_reports, py.fan_in AS payee_fan_in
           FROM cases c JOIN payments p ON p.id = c.payment_id
           JOIN users u ON u.id = c.user_id JOIN payees py ON py.id = p.payee_id
           {clause} ORDER BY c.score DESC, c.id DESC LIMIT ? OFFSET ?""",
        params + [limit, offset]).fetchall()
    return {"items": [_case_summary_dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@app.get("/cases/{case_id}")
def case_detail(case_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = _case_row(conn, case_id)
    detail = _case_summary_dict(row)
    feats = conn.execute("SELECT * FROM payment_features WHERE payment_id = ?", (row["payment_id"],)).fetchone()
    detail["features"] = dict(feats) if feats else {}
    detail["features"].pop("label", None)
    detail["timeline"] = [dict(r) for r in conn.execute(
        "SELECT stage, ts, channel, lang, text FROM scam_events WHERE payment_id = ? ORDER BY ts",
        (row["payment_id"],))]
    detail["behaviors"] = [dict(r) for r in conn.execute(
        "SELECT kind, ts, detail FROM behavior_events WHERE payment_id = ? ORDER BY ts",
        (row["payment_id"],))]
    detail["checkin"] = next(iter([dict(r) for r in conn.execute(
        "SELECT * FROM checkins WHERE case_id = ? ORDER BY id DESC", (case_id,))]), None)
    detail["report"] = next(iter([dict(r) for r in conn.execute(
        "SELECT id, report_id, completeness, status, reference_id, submitted_at FROM reports WHERE case_id = ? ORDER BY id DESC",
        (case_id,))]), None)
    detail["graph"] = explain.build_case_graph(conn, case_id)
    return detail


@app.post("/cases/{case_id}/checkin")
def answer_checkin(case_id: int, req: CheckinRequest, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = _case_row(conn, case_id)
    status = {"confirm": "confirmed", "deny": "denied", "unsure": "unsure"}[req.answer]
    now = _now()
    conn.execute("INSERT INTO checkins(case_id, sent_at, tier, answer, answered_at) VALUES (?,?,?,?,?)",
                 (case_id, now, "direct_checkin", req.answer, now))
    conn.execute("UPDATE cases SET status = ?, checkin_state = 'answered', answered_at = ? WHERE id = ?",
                 (status, now, case_id))
    conn.commit()
    return {"ok": True, "case_id": case_id, "status": status,
            "note": "Customer confirmation recorded. Confirmation is the customer's — the system never accuses."}


@app.post("/cases/{case_id}/request-callback")
def request_callback(case_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    _case_row(conn, case_id)
    conn.execute("UPDATE cases SET risk_tier = 'critical' WHERE id = ?", (case_id,))
    conn.execute("INSERT INTO checkins(case_id, sent_at, tier) VALUES (?,?, 'human_callback')", (case_id, _now()))
    conn.commit()
    return {"ok": True, "case_id": case_id, "tier": "human_callback",
            "note": "A human agent will call the customer. Simulated — no call is placed."}


@app.post("/cases/{case_id}/dismiss")
def dismiss_case(case_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    _case_row(conn, case_id)
    conn.execute("UPDATE cases SET status = 'dismissed' WHERE id = ?", (case_id,))
    conn.commit()
    return {"ok": True, "case_id": case_id, "status": "dismissed"}


# ---------- reports ----------

@app.post("/cases/{case_id}/report")
def create_report(case_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = _case_row(conn, case_id)
    if row["status"] not in ("confirmed", "unsure"):
        raise HTTPException(409, "Report can be built only after the customer confirms or is unsure. "
                                 "The system never accuses or reports without customer confirmation.")
    existing = conn.execute("SELECT * FROM reports WHERE case_id = ? AND status = 'submitted' ORDER BY id DESC",
                            (case_id,)).fetchone()
    if existing:
        return {"id": existing["id"], "report_id": existing["report_id"],
                "payload": json.loads(existing["payload"]), "completeness": existing["completeness"],
                "status": existing["status"], "reference_id": existing["reference_id"],
                "submitted_at": existing["submitted_at"], "created_at": existing["created_at"], "reused": True}
    payload = report.build_payload(conn, case_id)
    now = _now()
    cur = conn.execute(
        """INSERT INTO reports(report_id, case_id, payload, completeness, status, created_at)
           VALUES (?,?,?,?, 'draft', ?)""",
        (payload["report_id"], case_id, json.dumps(payload), payload["completeness"], now))
    conn.commit()
    return {"id": cur.lastrowid, "report_id": payload["report_id"], "payload": payload,
            "completeness": payload["completeness"], "status": "draft", "reference_id": None,
            "submitted_at": None, "created_at": now, "reused": False}


@app.get("/reports/{report_id}")
def get_report(report_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        row = conn.execute("SELECT * FROM reports WHERE report_id = ?", (str(report_id),)).fetchone()
    if row is None:
        raise HTTPException(404, "report not found")
    return {"id": row["id"], "report_id": row["report_id"], "case_id": row["case_id"],
            "payload": json.loads(row["payload"]), "completeness": row["completeness"],
            "status": row["status"], "reference_id": row["reference_id"],
            "submitted_at": row["submitted_at"], "created_at": row["created_at"]}


@app.post("/reports/{report_id}/submit")
def submit_report(report_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "report not found")
    if row["status"] == "submitted":
        return {"ok": True, "reference_id": row["reference_id"], "status": "submitted",
                "submitted_at": row["submitted_at"], "note": "Already submitted (simulated)."}
    reference = "SIM-NCRB-" + uuid.uuid4().hex[:6].upper()
    now = _now()
    conn.execute("UPDATE reports SET status = 'submitted', reference_id = ?, submitted_at = ? WHERE id = ?",
                 (reference, now, row["id"]))
    conn.commit()
    return {"ok": True, "reference_id": reference, "status": "submitted", "submitted_at": now,
            "note": "Submission SIMULATED to a mock endpoint. No real bank or authority was notified."}


# ---------- templates ----------

@app.get("/templates")
def list_templates(status: Optional[str] = None, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    query, params = "SELECT * FROM templates", []
    if status:
        query += " WHERE status = ?"; params.append(status)
    query += " ORDER BY CASE status WHEN 'proposed' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END, novelty_score DESC, size DESC"
    rows = conn.execute(query, params).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        for key in ("stages", "script_samples", "top_terms"):
            d[key] = json.loads(d[key])
        items.append(d)
    return {"items": items, "total": len(items)}


@app.post("/templates/{template_id}/approve")
def approve_template(template_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    if conn.execute("SELECT id FROM templates WHERE id = ?", (template_id,)).fetchone() is None:
        raise HTTPException(404, "template not found")
    conn.execute("UPDATE templates SET status = 'approved' WHERE id = ?", (template_id,))
    conn.commit()
    return {"ok": True, "id": template_id, "status": "approved"}


@app.post("/templates/{template_id}/reject")
def reject_template(template_id: int, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    if conn.execute("SELECT id FROM templates WHERE id = ?", (template_id,)).fetchone() is None:
        raise HTTPException(404, "template not found")
    conn.execute("UPDATE templates SET status = 'rejected' WHERE id = ?", (template_id,))
    conn.commit()
    return {"ok": True, "id": template_id, "status": "rejected"}


# ---------- budget ----------

@app.post("/budget/simulate")
def budget_simulate(req: BudgetSimulateRequest) -> dict[str, Any]:
    params = budget.BudgetParams.from_dict(req.model_dump(exclude_none=True))
    conn = db.connect()
    try:
        return budget.simulate(conn, params)
    finally:
        conn.close()


# ---------- metrics / demo ----------

@app.get("/metrics")
def metrics() -> dict[str, Any]:
    import pathlib
    path = pathlib.Path(__file__).resolve().parent.parent / "data" / "metrics.json"
    if not path.exists():
        raise HTTPException(503, "metrics not generated yet — run `make seed` first")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/customer/overview")
def customer_overview(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    user = conn.execute("SELECT * FROM users WHERE id = 1").fetchone()
    if user is None:
        raise HTTPException(503, "database not seeded — run `make seed` first")
    payments = [dict(r) for r in conn.execute(
        """SELECT p.id, p.ts, p.amount, p.is_new_payee, p.call_active, p.scam_type, p.is_demo,
                  py.handle AS payee_handle, py.name AS payee_name
           FROM payments p JOIN payees py ON py.id = p.payee_id
           WHERE p.user_id = 1 ORDER BY p.ts DESC LIMIT 12""")]
    case = conn.execute(
        """SELECT c.id FROM cases c JOIN payments p ON p.id = c.payment_id
           WHERE p.is_demo = 1""").fetchone()
    return {"user": dict(user), "payments": payments,
            "demo_case_id": case["id"] if case else None, "synthetic_data": True}


@app.post("/demo/story")
def demo_story(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    """Reset the deterministic demo case so the story can be replayed."""
    demo_pay = conn.execute("SELECT * FROM payments WHERE is_demo = 1").fetchone()
    if demo_pay is None:
        raise HTTPException(503, "demo payment not found — run `make seed` first")
    case = conn.execute("SELECT * FROM cases WHERE payment_id = ?", (demo_pay["id"],)).fetchone()
    if case is None:
        score = 0.93
        conn.execute(
            """INSERT INTO cases(payment_id, user_id, score, risk_tier, status, reasons, checkin_state, created_at)
               VALUES (?,?,?, 'critical', 'open', ?, 'not_sent', ?)""",
            (demo_pay["id"], demo_pay["user_id"], score,
             json.dumps(["New payee + active call + payment under time pressure",
                         "Amount is far above this customer's usual spend",
                         "Customer searched for how to reverse a UPI payment"]), _now()))
        conn.commit()
        case = conn.execute("SELECT * FROM cases WHERE payment_id = ?", (demo_pay["id"],)).fetchone()
    else:
        conn.execute("DELETE FROM checkins WHERE case_id = ?", (case["id"],))
        conn.execute("DELETE FROM reports WHERE case_id = ?", (case["id"],))
        conn.execute("UPDATE cases SET status = 'open', checkin_state = 'not_sent', answered_at = NULL WHERE id = ?",
                     (case["id"],))
        conn.commit()
    payee = conn.execute("SELECT * FROM payees WHERE id = ?", (demo_pay["payee_id"],)).fetchone()
    return {
        "case_id": case["id"], "payment_id": demo_pay["id"], "user_name": "Meena Devi",
        "amount": demo_pay["amount"], "payee_handle": payee["handle"], "payment_ts": demo_pay["ts"],
        "story": ["Fake electricity-department call (hinglish, voice_call)",
                  "Meena pays Rs 80,000 to a new payee while the caller is on the line",
                  "Post-payment distress: 3 balance checks, reversal search, 1930 helpline, payee unreachable",
                  "Bank's model flags the case; customer gets a gentle, non-accusatory check-in"],
        "synthetic_data": True,
    }


@app.post("/demo/reset")
def demo_reset(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    return demo_story(conn)
