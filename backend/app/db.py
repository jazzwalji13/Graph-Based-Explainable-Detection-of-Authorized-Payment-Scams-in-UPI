"""SQLite setup and helpers. Plain sqlite3, dict rows, WAL mode."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(os.environ.get("SCAM_REPORT_DB", DATA_DIR / "scam_report.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  segment TEXT NOT NULL,
  city TEXT NOT NULL,
  avg_amount REAL NOT NULL,
  amount_stddev REAL NOT NULL,
  monthly_frequency REAL NOT NULL,
  hour_start INTEGER NOT NULL,
  hour_end INTEGER NOT NULL,
  device_os TEXT NOT NULL,
  device_age_months INTEGER NOT NULL,
  biometric_enabled INTEGER NOT NULL,
  has_fd INTEGER NOT NULL,
  fd_amount REAL NOT NULL,
  credit_limit REAL NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payees (
  id INTEGER PRIMARY KEY,
  handle TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  prior_reports INTEGER NOT NULL DEFAULT 0,
  fan_in INTEGER NOT NULL DEFAULT 0,
  is_synthetic_scam INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  payee_id INTEGER NOT NULL REFERENCES payees(id),
  ts TEXT NOT NULL,
  day_index INTEGER NOT NULL,
  amount REAL NOT NULL,
  channel TEXT NOT NULL DEFAULT 'UPI',
  call_active INTEGER NOT NULL DEFAULT 0,
  app_switches INTEGER NOT NULL DEFAULT 0,
  hesitation_secs INTEGER NOT NULL DEFAULT 10,
  is_new_payee INTEGER NOT NULL DEFAULT 0,
  is_scam INTEGER NOT NULL DEFAULT 0,
  scam_type TEXT,
  scam_run_id TEXT,
  hard_negative INTEGER NOT NULL DEFAULT 0,
  hard_negative_kind TEXT,
  is_demo INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_day ON payments(day_index);
CREATE TABLE IF NOT EXISTS scam_events (
  id INTEGER PRIMARY KEY,
  payment_id INTEGER NOT NULL REFERENCES payments(id),
  stage TEXT NOT NULL,
  ts TEXT NOT NULL,
  channel TEXT NOT NULL,
  lang TEXT NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scam_events_payment ON scam_events(payment_id);
CREATE TABLE IF NOT EXISTS behavior_events (
  id INTEGER PRIMARY KEY,
  payment_id INTEGER NOT NULL REFERENCES payments(id),
  kind TEXT NOT NULL,
  ts TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_behavior_payment ON behavior_events(payment_id);
CREATE TABLE IF NOT EXISTS payment_features (
  payment_id INTEGER PRIMARY KEY REFERENCES payments(id),
  new_payee REAL, amount_z REAL, first_high_value REAL, hour_of_day REAL,
  is_unusual_hour REAL, call_active REAL, app_switches REAL, hesitation_secs REAL,
  post_balance_checks REAL, post_reversal_search REAL, post_support_contact REAL,
  post_payee_contact_failed REAL, fd_break REAL, loan_taken REAL,
  payee_prior_reports REAL, payee_fan_in REAL, urgency_score REAL,
  authority_score REAL, threat_score REAL, text_risk REAL,
  template_match REAL, stage_count REAL, label INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY,
  payment_id INTEGER NOT NULL UNIQUE REFERENCES payments(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  score REAL NOT NULL,
  risk_tier TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  reasons TEXT NOT NULL DEFAULT '[]',
  checkin_state TEXT NOT NULL DEFAULT 'not_sent',
  created_at TEXT NOT NULL,
  answered_at TEXT
);
CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY,
  case_id INTEGER NOT NULL REFERENCES cases(id),
  sent_at TEXT NOT NULL,
  tier TEXT NOT NULL,
  answer TEXT,
  answered_at TEXT
);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY,
  report_id TEXT UNIQUE NOT NULL,
  case_id INTEGER NOT NULL REFERENCES cases(id),
  payload TEXT NOT NULL,
  completeness REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  submitted_at TEXT,
  reference_id TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS templates (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  scam_type TEXT NOT NULL,
  hook TEXT NOT NULL,
  claimed_identity TEXT NOT NULL,
  urgency_cue TEXT NOT NULL,
  payment_ask TEXT NOT NULL,
  channel TEXT NOT NULL,
  stages TEXT NOT NULL,
  script_samples TEXT NOT NULL,
  top_terms TEXT NOT NULL,
  novelty_score REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'proposed',
  size INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS budget_log (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  ts TEXT NOT NULL,
  case_id INTEGER
);
"""


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def wipe(conn: sqlite3.Connection) -> None:
    for table in [
        "budget_log", "reports", "checkins", "cases", "payment_features",
        "behavior_events", "scam_events", "payments", "payees", "templates", "users", "meta",
    ]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
