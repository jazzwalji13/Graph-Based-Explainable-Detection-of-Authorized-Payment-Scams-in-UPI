"""Run backend (FastAPI on :8011) and frontend (Vite on :5173) together."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
IS_WIN = os.name == "nt"
PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def main() -> int:
    if not PY.exists():
        raise SystemExit("venv not found — run `make setup` first")
    if not (FRONTEND / "node_modules").exists():
        raise SystemExit("frontend deps not installed — run `make setup` first")

    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm not found — install Node.js 18+")

    backend = subprocess.Popen(
        [str(PY), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011", "--reload"],
        cwd=BACKEND, env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    frontend = subprocess.Popen(
        [npm, "run", "dev"], cwd=FRONTEND, env={**os.environ, "BROWSER": "none"},
        shell=IS_WIN,
    )
    print("\n  SCAM-REPORT dev servers")
    print("  Backend : http://localhost:8011  (docs at /docs)")
    print("  Frontend: http://localhost:5173\n")
    print("  Ctrl+C to stop both.\n")

    def stop(*_: object) -> None:
        for proc in (frontend, backend):
            try:
                if IS_WIN:
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGINT)
            except Exception:
                pass

    try:
        signal.signal(signal.SIGINT, stop)
        if IS_WIN:
            signal.signal(signal.SIGBREAK, stop)  # type: ignore[attr-defined]
        while True:
            if backend.poll() is not None:
                print("[dev] backend exited; stopping frontend")
                stop()
                return backend.returncode or 1
            if frontend.poll() is not None:
                print("[dev] frontend exited; stopping backend")
                stop()
                return frontend.returncode or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
