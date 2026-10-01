"""Print checkpoint status counts per model for a stage (no API calls)."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "core"
    out = {}
    for model_dir in sorted((ROOT / "data" / stage).iterdir()):
        db = model_dir / "checkpoint.sqlite"
        if db.exists():
            con = sqlite3.connect(db)
            out[model_dir.name] = dict(con.execute("SELECT status, COUNT(*) FROM trials GROUP BY status").fetchall())
            con.close()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
