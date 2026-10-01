"""Detached orchestrator: after a family's core arm finishes, run its frozen
robustness stages in plan order (template, order, cue location), pinned to the
freeze revision. Never touches the core checkpoint. Logs to logs/orchestrator.log."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FREEZE_REVISION = "33bfa10f70a6ca0efefc7a7ba685cbb60aea17fa"
ORDER = ("robust_template", "robust_order", "robust_cue_location")
MODEL_DIR = {"google_gemini": "gemini-3.1-flash-lite", "mistral": "ministral-14b-2512"}


def log(msg: str) -> None:
    with (ROOT / "logs" / "orchestrator.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n")


def core_done(family: str) -> bool:
    db = ROOT / "data" / "core" / MODEL_DIR[family] / "checkpoint.sqlite"
    con = sqlite3.connect(db)
    counts = dict(con.execute("SELECT status, COUNT(*) FROM trials GROUP BY status").fetchall())
    con.close()
    return counts.get("pending", 0) == 0 and counts.get("running", 0) == 0


def main() -> None:
    family = sys.argv[1]
    log(f"orchestrator start family={family}")
    while not core_done(family):
        time.sleep(300)
    log(f"core arm complete family={family}")
    for stage in ORDER:
        log(f"start {stage} family={family}")
        with (ROOT / "logs" / f"{stage}_{family}.log").open("a", encoding="utf-8") as out:
            rc = subprocess.call([sys.executable, "scripts/run_experiment.py", "--stage", stage, "--family", family,
                                  "--code-revision", FREEZE_REVISION], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
        log(f"end {stage} family={family} rc={rc}")
    log(f"orchestrator done family={family}")


if __name__ == "__main__":
    main()
