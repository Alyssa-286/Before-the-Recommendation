"""Stable Phase 1 failure categories and JSONL failure-event storage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import os
from pathlib import Path

from .output_parser import ParseStatus


FAILURE_TAXONOMY_VERSION = "1.0.0"


class FailureCategory(StrEnum):
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    REFUSAL = "refusal"
    INVALID_JSON = "invalid_json"
    SCHEMA_VALIDATION_FAILURE = "schema_validation_failure"
    MALFORMED_RESPONSE = "malformed_response"
    CATALOG_INSPECTION_MISSING = "catalog_inspection_missing"
    CLARIFICATION_ORDER_VIOLATION = "clarification_order_violation"
    INTERFACE_CONTRACT_VIOLATION = "interface_contract_violation"
    SIMULATED_ANSWER_MISMATCH = "simulated_answer_mismatch"
    UNSUPPORTED_CLARIFICATION_TARGET = "unsupported_clarification_target"
    AGENT_EXECUTION_FAILURE = "agent_execution_failure"
    RETRY_EXECUTION_FAILURE = "retry_execution_failure"
    CHECKPOINT_CONFLICT = "checkpoint_conflict"
    CHECKPOINT_CORRUPTION = "checkpoint_corruption"
    TRACE_WRITE_FAILURE = "trace_write_failure"
    SCORING_FAILURE = "scoring_failure"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class FailureEvent:
    category: FailureCategory
    stage: str
    message: str
    recoverable: bool
    attempt_number: int | None = None
    detail_code: str | None = None

    def __post_init__(self) -> None:
        if not self.stage.strip() or not self.message.strip():
            raise ValueError("Failure stage and message must be non-empty.")
        if self.attempt_number is not None and self.attempt_number < 1:
            raise ValueError("attempt_number must be positive when provided.")

    def as_dict(self) -> dict[str, object]:
        return {
            "category": self.category.value,
            "stage": self.stage,
            "message": self.message,
            "recoverable": self.recoverable,
            "attempt_number": self.attempt_number,
            "detail_code": self.detail_code,
        }


def category_for_parse_status(status: ParseStatus) -> FailureCategory | None:
    return {
        ParseStatus.VALID: None,
        ParseStatus.INVALID_JSON: FailureCategory.INVALID_JSON,
        ParseStatus.SCHEMA_VALIDATION_FAILURE: FailureCategory.SCHEMA_VALIDATION_FAILURE,
        ParseStatus.MALFORMED_RESPONSE: FailureCategory.MALFORMED_RESPONSE,
    }[status]


def classify_exception(exc: BaseException, *, retry: bool = False) -> FailureCategory:
    """Map common transport/runtime exception classes without storing secrets."""
    if isinstance(exc, TimeoutError):
        return FailureCategory.TIMEOUT
    if retry:
        return FailureCategory.RETRY_EXECUTION_FAILURE
    return FailureCategory.AGENT_EXECUTION_FAILURE


class JsonlFailureLogger:
    """Append one taxonomy event per line and never discard malformed history."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, trial_id: str, failure: FailureEvent) -> None:
        if not trial_id.strip():
            raise ValueError("trial_id must be non-empty.")
        row = {
            "record_type": "failure_event",
            "taxonomy_version": FAILURE_TAXONOMY_VERSION,
            "trial_id": trial_id,
            "failure": failure.as_dict(),
        }
        _append_jsonl(self.path, row)

    def read_all(self) -> tuple[dict[str, object], ...]:
        return tuple(_read_jsonl(self.path))


def _append_jsonl(path: Path, row: dict[str, object]) -> None:
    encoded = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    try:
        with path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    with path.open("rb") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            try:
                row = json.loads(raw_line)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError(f"Invalid JSONL record at {path}:{line_number}.") from exc
            if not isinstance(row, dict):
                raise ValueError(f"JSONL record at {path}:{line_number} is not an object.")
            rows.append(row)
    return rows
