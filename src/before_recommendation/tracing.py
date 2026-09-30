"""Typed trial identity and append-only JSONL trace storage."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

from .failures import FailureEvent, _read_jsonl
from .output_parser import OutputParseResult


TRACE_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class TrialIdentity:
    scenario_id: str
    profile_id: str
    goal_condition: str
    marketing_condition: str
    model_family: str
    model_version: str
    repetition: int
    prompt_template_id: str
    experiment_version: str
    config_sha256: str
    random_seed: int
    code_revision: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.scenario_id, self.profile_id, self.goal_condition, self.marketing_condition,
            self.model_family, self.model_version, self.prompt_template_id, self.experiment_version,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Trial identity text fields must be non-empty.")
        if self.repetition < 1:
            raise ValueError("repetition must be positive.")
        if len(self.config_sha256) != 64 or any(char not in "0123456789abcdef" for char in self.config_sha256):
            raise ValueError("config_sha256 must be a lowercase SHA-256 digest.")
        if self.code_revision is not None and (
            len(self.code_revision) < 7
            or len(self.code_revision) > 64
            or any(char not in "0123456789abcdef" for char in self.code_revision)
        ):
            raise ValueError("code_revision must be a lowercase Git object ID or null.")

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "profile_id": self.profile_id,
            "goal_condition": self.goal_condition,
            "marketing_condition": self.marketing_condition,
            "model_family": self.model_family,
            "model_version": self.model_version,
            "repetition": self.repetition,
            "prompt_template_id": self.prompt_template_id,
            "experiment_version": self.experiment_version,
            "config_sha256": self.config_sha256,
            "random_seed": self.random_seed,
            "code_revision": self.code_revision,
        }

    @property
    def trial_id(self) -> str:
        canonical = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class TraceEvent:
    sequence: int
    actor: str
    event_type: str
    payload: dict[str, object]

    def __post_init__(self) -> None:
        if self.sequence < 0 or not self.actor.strip() or not self.event_type.strip():
            raise ValueError("Trace event sequence, actor, and event_type are required.")

    def as_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "actor": self.actor,
            "event_type": self.event_type,
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class AgentVisibleInput:
    request_text: str
    catalog_listings: tuple[dict[str, object], ...]
    system_instruction: str | None = None
    api_parameters: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        prompt_material = json.dumps(
            {"request_text": self.request_text, "system_instruction": self.system_instruction},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {
            "request_text": self.request_text,
            "prompt_sha256": hashlib.sha256(prompt_material).hexdigest(),
            "system_instruction": self.system_instruction,
            "api_parameters": self.api_parameters or {},
            "catalog_listings": list(self.catalog_listings),
        }


@dataclass(frozen=True, slots=True)
class OutputAttemptTrace:
    attempt_number: int
    result: OutputParseResult

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive.")

    def raw_dict(self) -> dict[str, object]:
        raw_value = self.result.raw_output
        raw_text = raw_value if isinstance(raw_value, str) else None
        digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest() if raw_text is not None else None
        return {
            "attempt_number": self.attempt_number,
            "raw_response": raw_value,
            "raw_response_sha256": digest,
        }

    def derived_dict(self) -> dict[str, object]:
        return {
            "attempt_number": self.attempt_number,
            "parse_status": self.result.status.value,
            "parsed_output": self.result.data,
            "validation_errors": [
                {"path": error.path, "code": error.code, "message": error.message}
                for error in self.result.errors
            ],
            "schema_version": self.result.schema_version,
        }


@dataclass(frozen=True, slots=True)
class TrialTrace:
    identity: TrialIdentity
    started_at_utc: str
    completed_at_utc: str
    agent_visible_input: AgentVisibleInput
    events: tuple[TraceEvent, ...]
    attempts: tuple[OutputAttemptTrace, ...]
    derived_metrics: dict[str, object]
    evaluator_private: dict[str, object]
    failures: tuple[FailureEvent, ...] = ()

    def __post_init__(self) -> None:
        if not self.started_at_utc.endswith("Z") or not self.completed_at_utc.endswith("Z"):
            raise ValueError("Trace timestamps must be UTC ISO-8601 strings ending with Z.")
        if tuple(event.sequence for event in self.events) != tuple(range(len(self.events))):
            raise ValueError("Trace event sequence numbers must be contiguous from zero.")
        numbers = tuple(attempt.attempt_number for attempt in self.attempts)
        if numbers != tuple(range(1, len(numbers) + 1)):
            raise ValueError("Attempt numbers must be contiguous from one.")
        if len(self.attempts) > 2:
            raise ValueError("At most one recovery retry is supported.")

    def as_dict(self) -> dict[str, object]:
        return {
            "record_type": "trial_trace",
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "trial_id": self.identity.trial_id,
            "identity": self.identity.as_dict(),
            "timestamps": {"started_at_utc": self.started_at_utc, "completed_at_utc": self.completed_at_utc},
            "agent_visible": self.agent_visible_input.as_dict(),
            "events": [event.as_dict() for event in self.events],
            "raw": {"attempts": [attempt.raw_dict() for attempt in self.attempts]},
            "derived": {
                "attempts": [attempt.derived_dict() for attempt in self.attempts],
                "metrics": self.derived_metrics,
            },
            "evaluator_private": self.evaluator_private,
            "failures": [failure.as_dict() for failure in self.failures],
        }


class JsonlTraceLogger:
    """Append one complete trial trace per line; reject duplicates/corrupt history."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._trial_ids = {str(row["trial_id"]) for row in _read_jsonl(self.path) if row.get("record_type") == "trial_trace"}

    def append(self, trace: TrialTrace) -> None:
        row = trace.as_dict()
        trial_id = str(row["trial_id"])
        if trial_id in self._trial_ids:
            raise ValueError(f"Trial trace already exists for {trial_id}.")
        encoded = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with self.path.open("ab") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            raise
        self._trial_ids.add(trial_id)

    def read_all(self) -> tuple[dict[str, object], ...]:
        return tuple(_read_jsonl(self.path))


def trial_ids_for_config(records: Iterable[dict[str, object]]) -> tuple[str, ...]:
    return tuple(str(record["trial_id"]) for record in records)
