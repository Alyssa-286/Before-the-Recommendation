"""Transactional SQLite checkpointing with explicit resume/retry transitions."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
from pathlib import Path
import sqlite3
from typing import Iterator, Iterable

from .failures import FailureCategory
from .tracing import TrialIdentity


CHECKPOINT_SCHEMA_VERSION = 1


class CheckpointError(RuntimeError):
    """Base error for invalid checkpoint state or transitions."""


class CheckpointConfigurationMismatch(CheckpointError):
    """The requested configuration differs from the checkpoint's pinned run."""


class CheckpointConflict(CheckpointError):
    """A state transition or trial registration conflicts with recorded state."""


class CheckpointCorruption(CheckpointError):
    """The checkpoint has an unsupported or inconsistent schema."""


class TrialStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    trial_id: str
    identity: dict[str, object]
    status: TrialStatus
    attempt_count: int
    interruption_count: int
    explicit_requeue_count: int
    last_failure_category: str | None
    result_ref: str | None
    result_sha256: str | None
    updated_at_utc: str


class CheckpointStore:
    """One checkpoint file is pinned to one exact experiment config digest.

    Running rows are never silently considered pending. On startup, callers
    explicitly call :meth:`requeue_interrupted` before asking for pending work.
    Failed rows require :meth:`requeue_failed` with a documented reason.
    """

    def __init__(self, path: str | Path, config_sha256: str) -> None:
        if len(config_sha256) != 64 or any(char not in "0123456789abcdef" for char in config_sha256):
            raise ValueError("config_sha256 must be a lowercase SHA-256 digest.")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config_sha256 = config_sha256
        self._initialize()

    def register_trials(self, identities: Iterable[TrialIdentity]) -> tuple[str, ...]:
        newly_registered: list[str] = []
        with self._transaction() as connection:
            for identity in identities:
                if identity.config_sha256 != self.config_sha256:
                    raise CheckpointConfigurationMismatch(
                        "Trial identity config digest does not match this checkpoint."
                    )
                requested_revision = identity.code_revision or ""
                revision_row = connection.execute(
                    "SELECT value FROM metadata WHERE key='code_revision'"
                ).fetchone()
                if revision_row is None:
                    connection.execute(
                        "INSERT INTO metadata(key,value) VALUES('code_revision',?)",
                        (requested_revision,),
                    )
                elif str(revision_row[0]) != requested_revision:
                    raise CheckpointConfigurationMismatch(
                        "Checkpoint is pinned to a different code revision; use a new checkpoint file for changed code."
                    )
                trial_id = identity.trial_id
                identity_json = _canonical_json(identity.as_dict())
                existing = connection.execute(
                    "SELECT identity_json FROM trials WHERE trial_id = ?", (trial_id,)
                ).fetchone()
                if existing is not None:
                    if existing[0] != identity_json:
                        raise CheckpointConflict(f"Trial identity mismatch for {trial_id}.")
                    continue
                now = _utc_now()
                connection.execute(
                    """INSERT INTO trials (
                        trial_id, identity_json, status, attempt_count, interruption_count,
                        explicit_requeue_count, last_failure_category, result_ref,
                        result_sha256, updated_at_utc
                    ) VALUES (?, ?, ?, 0, 0, 0, NULL, NULL, NULL, ?)""",
                    (trial_id, identity_json, TrialStatus.PENDING.value, now),
                )
                self._event(connection, trial_id, "registered", {"status": TrialStatus.PENDING.value})
                newly_registered.append(trial_id)
        return tuple(newly_registered)

    def claim(self, trial_id: str) -> CheckpointRecord:
        with self._transaction() as connection:
            row = self._get_row(connection, trial_id)
            if row["status"] != TrialStatus.PENDING.value:
                raise CheckpointConflict(f"Cannot claim trial {trial_id} from state {row['status']}.")
            now = _utc_now()
            connection.execute(
                "UPDATE trials SET status=?, attempt_count=attempt_count+1, updated_at_utc=? WHERE trial_id=?",
                (TrialStatus.RUNNING.value, now, trial_id),
            )
            self._event(connection, trial_id, "claimed", {"attempt_number": int(row["attempt_count"]) + 1})
            return self._record(self._get_row(connection, trial_id))

    def complete(self, trial_id: str, result_ref: str, result_sha256: str | None = None) -> CheckpointRecord:
        if not result_ref.strip():
            raise ValueError("result_ref must be non-empty.")
        if result_sha256 is not None and (
            len(result_sha256) != 64 or any(char not in "0123456789abcdef" for char in result_sha256)
        ):
            raise ValueError("result_sha256 must be a lowercase SHA-256 digest.")
        with self._transaction() as connection:
            row = self._get_row(connection, trial_id)
            if row["status"] != TrialStatus.RUNNING.value:
                raise CheckpointConflict(f"Cannot complete trial {trial_id} from state {row['status']}.")
            now = _utc_now()
            connection.execute(
                "UPDATE trials SET status=?, result_ref=?, result_sha256=?, updated_at_utc=? WHERE trial_id=?",
                (TrialStatus.COMPLETED.value, result_ref, result_sha256, now, trial_id),
            )
            self._event(connection, trial_id, "completed", {"result_ref": result_ref, "result_sha256": result_sha256})
            return self._record(self._get_row(connection, trial_id))

    def fail(self, trial_id: str, category: FailureCategory) -> CheckpointRecord:
        with self._transaction() as connection:
            row = self._get_row(connection, trial_id)
            if row["status"] != TrialStatus.RUNNING.value:
                raise CheckpointConflict(f"Cannot fail trial {trial_id} from state {row['status']}.")
            now = _utc_now()
            connection.execute(
                "UPDATE trials SET status=?, last_failure_category=?, updated_at_utc=? WHERE trial_id=?",
                (TrialStatus.FAILED.value, category.value, now, trial_id),
            )
            self._event(connection, trial_id, "failed", {"category": category.value})
            return self._record(self._get_row(connection, trial_id))

    def requeue_interrupted(self) -> tuple[str, ...]:
        """Return running rows to pending after a process restart, recording each transition."""
        with self._transaction() as connection:
            rows = connection.execute("SELECT trial_id FROM trials WHERE status=? ORDER BY trial_id", (TrialStatus.RUNNING.value,)).fetchall()
            trial_ids = tuple(str(row[0]) for row in rows)
            for trial_id in trial_ids:
                now = _utc_now()
                connection.execute(
                    "UPDATE trials SET status=?, interruption_count=interruption_count+1, updated_at_utc=? WHERE trial_id=?",
                    (TrialStatus.PENDING.value, now, trial_id),
                )
                self._event(connection, trial_id, "interrupted_requeued", {"status": TrialStatus.PENDING.value})
            return trial_ids

    def requeue_failed(self, trial_id: str, documented_reason: str) -> CheckpointRecord:
        if not documented_reason.strip():
            raise ValueError("A documented reason is required to requeue a failed trial.")
        with self._transaction() as connection:
            row = self._get_row(connection, trial_id)
            if row["status"] != TrialStatus.FAILED.value:
                raise CheckpointConflict(f"Cannot requeue trial {trial_id} from state {row['status']}.")
            now = _utc_now()
            connection.execute(
                "UPDATE trials SET status=?, explicit_requeue_count=explicit_requeue_count+1, updated_at_utc=? WHERE trial_id=?",
                (TrialStatus.PENDING.value, now, trial_id),
            )
            self._event(connection, trial_id, "failed_requeued", {"documented_reason": documented_reason})
            return self._record(self._get_row(connection, trial_id))

    def pending_trial_ids(self) -> tuple[str, ...]:
        with self._connection() as connection:
            rows = connection.execute("SELECT trial_id FROM trials WHERE status=? ORDER BY trial_id", (TrialStatus.PENDING.value,)).fetchall()
            return tuple(str(row[0]) for row in rows)

    def get(self, trial_id: str) -> CheckpointRecord:
        with self._connection() as connection:
            return self._record(self._get_row(connection, trial_id))

    def list_records(self) -> tuple[CheckpointRecord, ...]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM trials ORDER BY trial_id").fetchall()
            return tuple(self._record(row) for row in rows)

    def events(self, trial_id: str | None = None) -> tuple[dict[str, object], ...]:
        with self._connection() as connection:
            if trial_id is None:
                rows = connection.execute("SELECT sequence, trial_id, event_type, at_utc, details_json FROM checkpoint_events ORDER BY sequence").fetchall()
            else:
                rows = connection.execute("SELECT sequence, trial_id, event_type, at_utc, details_json FROM checkpoint_events WHERE trial_id=? ORDER BY sequence", (trial_id,)).fetchall()
        return tuple({
            "sequence": int(row[0]),
            "trial_id": str(row[1]),
            "event_type": str(row[2]),
            "at_utc": str(row[3]),
            "details": json.loads(row[4]),
        } for row in rows)

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if user_version not in (0, CHECKPOINT_SCHEMA_VERSION):
                raise CheckpointCorruption(f"Unsupported checkpoint schema version {user_version}.")
            connection.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("""CREATE TABLE IF NOT EXISTS trials (
                trial_id TEXT PRIMARY KEY,
                identity_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','running','completed','failed')),
                attempt_count INTEGER NOT NULL,
                interruption_count INTEGER NOT NULL,
                explicit_requeue_count INTEGER NOT NULL,
                last_failure_category TEXT,
                result_ref TEXT,
                result_sha256 TEXT,
                updated_at_utc TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS checkpoint_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                trial_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                at_utc TEXT NOT NULL,
                details_json TEXT NOT NULL
            )""")
            connection.execute(f"PRAGMA user_version={CHECKPOINT_SCHEMA_VERSION}")

        with self._transaction() as connection:
            existing = connection.execute("SELECT value FROM metadata WHERE key='config_sha256'").fetchone()
            if existing is not None and str(existing[0]) != self.config_sha256:
                raise CheckpointConfigurationMismatch(
                    "Checkpoint is pinned to a different config SHA-256; use a new checkpoint file for changed configuration."
                )
            if existing is None:
                connection.execute("INSERT INTO metadata(key,value) VALUES('config_sha256',?)", (self.config_sha256,))
                connection.execute("INSERT INTO metadata(key,value) VALUES('schema_version',?)", (str(CHECKPOINT_SCHEMA_VERSION),))

    def _event(self, connection: sqlite3.Connection, trial_id: str, event_type: str, details: dict[str, object]) -> None:
        connection.execute(
            "INSERT INTO checkpoint_events(trial_id,event_type,at_utc,details_json) VALUES(?,?,?,?)",
            (trial_id, event_type, _utc_now(), _canonical_json(details)),
        )

    @staticmethod
    def _get_row(connection: sqlite3.Connection, trial_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown trial_id {trial_id}.")
        return row

    @staticmethod
    def _record(row: sqlite3.Row) -> CheckpointRecord:
        try:
            status = TrialStatus(str(row["status"]))
            identity_data = json.loads(str(row["identity_json"]))
        except (ValueError, json.JSONDecodeError, KeyError) as exc:
            raise CheckpointCorruption("Checkpoint contains an invalid trial record.") from exc
        if not isinstance(identity_data, dict):
            raise CheckpointCorruption("Checkpoint trial identity is not an object.")
        return CheckpointRecord(
            trial_id=str(row["trial_id"]),
            identity=identity_data,
            status=status,
            attempt_count=int(row["attempt_count"]),
            interruption_count=int(row["interruption_count"]),
            explicit_requeue_count=int(row["explicit_requeue_count"]),
            last_failure_category=None if row["last_failure_category"] is None else str(row["last_failure_category"]),
            result_ref=None if row["result_ref"] is None else str(row["result_ref"]),
            result_sha256=None if row["result_sha256"] is None else str(row["result_sha256"]),
            updated_at_utc=str(row["updated_at_utc"]),
        )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            else:
                connection.execute("COMMIT")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
