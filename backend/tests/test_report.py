from __future__ import annotations

import json

from app import db, report, simulator
from app.simulator import SCAM_TYPES


def _seeded(tmp_path, cfg):
    conn = db.connect(tmp_path / "test.db")
    simulator.generate(conn, cfg)
    return conn


def test_completeness_score_bounds(tmp_path):
    cfg = simulator.load_config()
    cfg.update({"seed": 11, "users": 30, "days": 30, "drift_start_day": 20})
    conn = _seeded(tmp_path, cfg)
    demo = conn.execute("SELECT id FROM payments WHERE is_demo = 1").fetchone()
    conn.execute(
        """INSERT INTO cases(payment_id, user_id, score, risk_tier, status, reasons, checkin_state, created_at, answered_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (demo["id"], 1, 0.95, "critical", "confirmed", json.dumps(["New payee + active call"]), "answered",
         "2026-11-10T09:00:00", "2026-11-10T09:05:00"))
    case_id = conn.execute("SELECT id FROM cases WHERE payment_id = ?", (demo["id"],)).fetchone()["id"]
    payload = report.build_payload(conn, case_id)
    assert 0.0 < payload["completeness"] <= 100.0
    for field in ["report_id", "timestamps", "payment_refs", "amount", "payee", "scam_type",
                  "stage_timeline", "first_contact_channel", "claimed_identity", "urgency_cues",
                  "communication_identifiers", "evidence", "model", "customer_confirmation", "consent"]:
        assert field in payload, f"missing field {field}"
    assert payload["synthetic_data_notice"].startswith("SYNTHETIC")
    assert payload["consent"]["share_with_bank"] is True
    # full-signal non-accusatory report should score high
    assert payload["completeness"] >= 85.0
    conn.close()


def test_completeness_penalises_missing():
    minimal = {
        "payment_refs": {}, "amount": None, "payee": {}, "scam_type": "unknown",
        "stage_timeline": [], "first_contact_channel": "unknown", "claimed_identity": "Not captured",
        "urgency_cues": [], "communication_identifiers": {}, "evidence": [],
        "model": {"reason_codes": []}, "customer_confirmation": {"status": "pending"},
        "consent": {"share_with_bank": False, "share_with_ncrb_portal": False, "anonymous_analytics": False},
    }
    assert report.completeness_score(minimal) == 0.0


def test_all_scam_types_have_scripts_and_stats():
    for key, spec in SCAM_TYPES.items():
        assert spec["label"]
        assert spec["amount_range"][0] < spec["amount_range"][1]
        assert 0 < spec["new_payee_p"] <= 1
        assert spec["channels"]
        from app.simulator import SCRIPTS
        assert key in SCRIPTS
        for lang in ("en", "hi", "hinglish"):
            assert lang in SCRIPTS[key], f"{key} missing {lang}"
