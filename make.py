"""Cross-platform task runner. Mirrors the Makefile so the project also works
on machines without `make` (Windows): `python make.py setup|seed|dev|test|build`."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
IS_WIN = os.name == "nt"
PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.check_call([str(c) for c in cmd], cwd=cwd or ROOT)


def setup() -> None:
    if not VENV.exists():
        _run([sys.executable, "-m", "venv", str(VENV)])
    _run([PY, "-m", "pip", "install", "--upgrade", "pip"])
    _run([PY, "-m", "pip", "install", "-r", "backend/requirements.txt"])
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm not found — install Node.js 18+")
    _run([npm, "install"], cwd=ROOT / "frontend")


def seed() -> None:
    _run([PY, "-m", "app.seed"], cwd=ROOT / "backend")


def dev() -> None:
    _run([PY, "scripts/dev.py"])


def test() -> None:
    _run([PY, "-m", "pytest", "tests", "-q"], cwd=ROOT / "backend")
    npm = shutil.which("npm")
    _run([npm, "run", "typecheck"], cwd=ROOT / "frontend")
    _run([npm, "run", "build"], cwd=ROOT / "frontend")


def build() -> None:
    npm = shutil.which("npm")
    _run([npm, "run", "build"], cwd=ROOT / "frontend")


TASKS = {"setup": setup, "seed": seed, "dev": dev, "test": test, "build": build}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        raise SystemExit(f"usage: python make.py [{'|'.join(TASKS)}]")
    TASKS[sys.argv[1]]()
