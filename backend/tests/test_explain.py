from __future__ import annotations

import json

import pytest

from app import db, simulator


@pytest.fixture()
def seeded(tmp_path):
    from app import features
    cfg = simulator.load_config()
    cfg.update({"seed": 42, "users": 60, "days": 40, "drift_start_day": 25})
    conn = db.connect(tmp_path / "test.db")
    simulator.generate(conn, cfg)
    features.store_features(conn, features.build_frame(conn))
    yield conn
    conn.close()


def _make_case(conn):
    demo = conn.execute("SELECT * FROM payments WHERE is_demo = 1").fetchone()
    conn.execute(
        """INSERT INTO cases(payment_id, user_id, score, risk_tier, status, reasons, checkin_state, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (demo["id"], demo["user_id"], 0.91, "critical", "open",
         json.dumps(["New payee + active call + payment under time pressure"]), "not_sent",
         "2026-11-10T09:00:00"))
    return conn.execute("SELECT id FROM cases WHERE payment_id = ?", (demo["id"],)).fetchone()["id"]


def test_case_graph_schema(seeded, monkeypatch):
    from app import explain, model

    monkeypatch.setattr(model, "load_model", lambda: {"lgbm": None, "calibrator": None,
                                                      "features": explain.FEATURE_COLUMNS})
    import numpy as np
    monkeypatch.setattr(explain, "_contrib_map", lambda row: {c: float(i + 1) * 0.01 for i, c in enumerate(explain.FEATURE_COLUMNS)})

    case_id = _make_case(seeded)
    graph = explain.build_case_graph(seeded, case_id)

    assert graph["case_id"] == case_id
    assert 0.0 <= graph["confidence"] <= 1.0
    assert graph["nodes"] and graph["edges"]
    node_ids = {n["id"] for n in graph["nodes"]}
    for n in graph["nodes"]:
        assert n["type"] in ("event", "stage", "payment", "behavior")
        assert isinstance(n["label"], str) and n["label"]
        assert isinstance(n["timestamp"], str)
        assert isinstance(n["contribution"], float)
        assert n["highlighted"] in (True, False)
    for e in graph["edges"]:
        assert e["type"] in ("time_order", "supports_stage")
        assert e["source"] in node_ids and e["target"] in node_ids
    assert sum(1 for n in graph["nodes"] if n["highlighted"]) >= 1
    assert graph["reasons"] == ["New payee + active call + payment under time pressure"]
    assert graph["top_features"] and set(graph["top_features"][0]) <= {"feature", "contribution", "share"}
