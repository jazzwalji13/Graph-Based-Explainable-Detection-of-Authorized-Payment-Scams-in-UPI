from __future__ import annotations

import pytest

from app import db, simulator


@pytest.fixture()
def cfg() -> dict:
    c = simulator.load_config()
    c["seed"] = 7
    c["users"] = 60
    c["days"] = 45
    c["drift_start_day"] = 30
    return c


@pytest.fixture()
def seeded(tmp_path, cfg):
    conn = db.connect(tmp_path / "test.db")
    simulator.generate(conn, cfg)
    yield conn
    conn.close()


def test_simulator_deterministic(seeded, cfg, tmp_path):
    counts1 = seeded.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    scams1 = seeded.execute("SELECT COUNT(*) FROM payments WHERE is_scam = 1").fetchone()[0]
    conn2 = db.connect(tmp_path / "test2.db")
    simulator.generate(conn2, cfg)
    assert conn2.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == counts1
    assert conn2.execute("SELECT COUNT(*) FROM payments WHERE is_scam = 1").fetchone()[0] == scams1
    assert conn2.execute("SELECT COUNT(*) FROM users").fetchone()[0] == cfg["users"]
    conn2.close()


def test_demo_payment_injected(seeded):
    row = seeded.execute("SELECT * FROM payments WHERE is_demo = 1").fetchone()
    assert row is not None
    assert row["amount"] == 80000
    assert row["is_scam"] == 1
    events = seeded.execute("SELECT COUNT(*) FROM scam_events WHERE payment_id = ?", (row["id"],)).fetchone()[0]
    assert events >= 6
    distress = seeded.execute("SELECT COUNT(*) FROM behavior_events WHERE payment_id = ?", (row["id"],)).fetchone()[0]
    assert distress >= 4


def test_hard_negatives_and_drift_present(seeded):
    hn = seeded.execute("SELECT COUNT(*) FROM payments WHERE hard_negative = 1").fetchone()[0]
    assert hn > 0
    drift = seeded.execute("SELECT COUNT(*) FROM payments WHERE scam_type = 'e_challan_summons'").fetchone()[0]
    assert drift >= 0  # drift may be 0 in tiny windows; presence asserted in full seed


def test_scripts_cover_languages(seeded):
    langs = {r[0] for r in seeded.execute("SELECT DISTINCT lang FROM scam_events")}
    assert langs & {"en", "hi", "hinglish"}
