"""Load repository-local runtime settings without exposing their values."""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Iterable

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_runtime_environment(
    dotenv_path: str | Path | None = None,
    *,
    names: Iterable[str] | None = None,
) -> bool:
    """Load a local .env with process variables taking precedence.

    Only requested names are copied into the process environment. Existing
    process variables take precedence. Tests may provide a temporary path.
    The return value reports whether a file was read; it never contains or
    derives information from credential values.
    """
    path = Path(dotenv_path) if dotenv_path is not None else PROJECT_ROOT / ".env"
    if not path.is_file():
        return False
    values = dotenv_values(path, interpolate=False, encoding="utf-8")
    requested = tuple(names) if names is not None else tuple(values)
    for name in requested:
        if not name or os.environ.get(name):
            continue
        value = values.get(name)
        if isinstance(value, str) and value:
            os.environ[name] = value
    return True
