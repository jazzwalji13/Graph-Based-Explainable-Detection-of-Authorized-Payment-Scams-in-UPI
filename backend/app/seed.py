"""One-command seed: simulator -> features -> discovery -> model -> cases -> metrics."""
from __future__ import annotations

import json
import sqlite3
import sys
from typing import Any

from . import budget, db, discovery, evaluate, features, model, simulator


def run_pipeline(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = simulator.load_config()
    if overrides:
        allowed = {"seed", "users", "days", "scam_rate", "flag_threshold", "drift_start_day"}
        for k, v in overrides.items():
            if k in allowed and v is not None:
                cfg[k] = v
    conn = db.connect()
    try:
        sim_summary = simulator.generate(conn, cfg)
        df = features.build_frame(conn)
        features.store_features(conn, df)
        disc = discovery.build(conn)
        model_info = model.train_and_save(conn, seed=cfg["seed"])
        # reload to pick up template_match written by discovery
        flagged = model.flag_cases(conn, cfg["flag_threshold"])
        metrics = evaluate.run(conn)
        seed_info = {
            "simulator": sim_summary, "discovery": disc, "model": model_info,
            "cases_flagged": flagged, "config": {k: cfg[k] for k in ("seed", "users", "days", "scam_rate", "flag_threshold")},
        }
        db.set_meta(conn, "seed_summary", json.dumps(seed_info))
        return seed_info
    finally:
        conn.close()


def main() -> int:
    overrides = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
    summary = run_pipeline(overrides)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
