"""Checkpointed batch execution of live trials under the frozen retry rules.

Two distinct retry mechanisms exist and are logged separately:

* Transport throttling: an HTTP 429/5xx response carries no model output, so
  the identical request is re-sent after a backoff (bounded, every event is
  appended to ``transport_events.jsonl``). This never alters model content.
* Technical trial retry: a trial whose provider call still fails is re-run
  from its first turn exactly once, with the original attempt's trace, raw I/O
  and failure records preserved in attempt-numbered files.

Refusals, protocol/behaviour violations and parser failures are never re-run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .checkpoint import CheckpointStore, TrialStatus
from .failures import FailureCategory, JsonlFailureLogger
from .live_controller import CORE_VARIANT, LiveTrialController, ProtocolVariant, RawModelIOLogger, live_trial_config_sha256
from .model_adapters import HttpResponse, ModelConfig, _http_post_json, make_adapter
from .prompts import GoalCondition, generate_request
from .scenarios import ResearchScenario
from .tracing import JsonlTraceLogger, TrialIdentity


RUNNER_VERSION = "1.0.0"
TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})
# 429 bodies that signal exhausted billing/daily quota are not transient.
NON_TRANSIENT_MARKERS = (b"insufficient_quota", b"credit_balance", b"PerDay")
MAX_TRANSPORT_RETRIES = 6
TECHNICAL_RETRY_CATEGORIES = frozenset({
    FailureCategory.API_ERROR.value,
    FailureCategory.TIMEOUT.value,
    FailureCategory.RATE_LIMIT.value,
    FailureCategory.MALFORMED_RESPONSE.value,
})
TECHNICAL_RETRY_REASON = "frozen technical-retry rule: one full re-run after a provider/transport failure"

_context = threading.local()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def current_code_revision(repository_root: Path) -> str:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    return revision


class _LockedJsonl:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def append(self, record: dict[str, object]) -> None:
        encoded = (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        with self.lock:
            with self.path.open("ab") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())


class _LockedRawIO(RawModelIOLogger):
    def __init__(self, path: str | Path, lock: threading.Lock) -> None:
        super().__init__(path)
        self._lock = lock

    def append(self, record: dict[str, object]) -> None:
        with self._lock:
            super().append(record)


class _LockedTrace(JsonlTraceLogger):
    def __init__(self, path: str | Path, lock: threading.Lock) -> None:
        super().__init__(path)
        self._lock = lock

    def append(self, trace) -> None:  # type: ignore[override]
        with self._lock:
            super().append(trace)


class _LockedFailures(JsonlFailureLogger):
    def __init__(self, path: str | Path, lock: threading.Lock) -> None:
        super().__init__(path)
        self._lock = lock

    def record(self, trial_id, failure) -> None:  # type: ignore[override]
        with self._lock:
            super().record(trial_id, failure)


class ThrottledTransport:
    """Pace requests per model and re-send only responses without model output."""

    def __init__(self, min_interval_seconds: float, events: _LockedJsonl, model_id: str) -> None:
        self.min_interval = min_interval_seconds
        self.events = events
        self.model_id = model_id
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def _wait_for_slot(self) -> None:
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self.min_interval
        delay = slot - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    def __call__(self, endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
        attempt = 0
        while True:
            self._wait_for_slot()
            try:
                response = _http_post_json(endpoint, headers, body, timeout)
            except (TimeoutError, OSError) as exc:
                if attempt >= MAX_TRANSPORT_RETRIES:
                    raise
                status, retry_after, kind = None, None, type(exc).__name__
            else:
                if (
                    response.status_code not in TRANSIENT_STATUS
                    or attempt >= MAX_TRANSPORT_RETRIES
                    or any(marker in response.body for marker in NON_TRANSIENT_MARKERS)
                ):
                    return response
                status, retry_after, kind = response.status_code, response.retry_after, "http_status"
            attempt += 1
            backoff = min(120.0, 4.0 * (2 ** (attempt - 1))) + random.uniform(0, 2)
            try:
                if retry_after is not None:
                    backoff = max(backoff, float(retry_after))
            except ValueError:
                pass
            self.events.append({
                "record_type": "transport_retry_event",
                "at_utc": _utc_now(),
                "model_id": self.model_id,
                "trial_id": getattr(_context, "trial_id", None),
                "trial_attempt": getattr(_context, "attempt", None),
                "status_code": status,
                "exception_type": None if kind == "http_status" else kind,
                "retry_after": retry_after,
                "transport_attempt": attempt,
                "backoff_seconds": round(backoff, 3),
                "request_body_sha256": hashlib.sha256(body).hexdigest(),
            })
            time.sleep(backoff)


DAILY_QUOTA_MARKERS = (b"PerDay", b"per day", b"daily")
MAX_POOL_TRANSIENT_RETRIES = 12


def _next_daily_reset_epoch(now: float | None = None) -> float:
    """Gemini RPD resets at midnight Pacific; 07:05 UTC (PDT) is used as a safe bound."""
    current = datetime.fromtimestamp(now or time.time(), timezone.utc)
    reset = current.replace(hour=7, minute=5, second=0, microsecond=0)
    if reset <= current:
        reset = datetime.fromtimestamp(reset.timestamp() + 86400, timezone.utc)
    return reset.timestamp()


class CredentialPoolTransport:
    """Pace each credential of ONE model separately and never exceed provider limits.

    Credentials are execution resources for the same model (never different
    families). A request is sent with the bearer credential whose next pacing slot
    is earliest. HTTP 429 per-minute responses delay that credential; daily-quota
    429 responses suspend it until the next daily reset; 5xx responses are re-sent
    after backoff. Such responses carry no model output, so re-sends never alter
    model content. Every request is logged with the credential VARIABLE NAME only;
    all pool secrets are redacted from response bytes.
    """

    def __init__(self, credential_envs, min_interval_seconds, events, credential_log, model_id):
        if not credential_envs:
            raise ValueError("At least one credential variable is required.")
        self.credential_envs = tuple(credential_envs)
        self.min_interval = min_interval_seconds
        self.events = events
        self.credential_log = credential_log
        self.model_id = model_id
        self._lock = threading.Lock()
        self._next_slot = {name: 0.0 for name in self.credential_envs}
        self._suspended_until = {name: 0.0 for name in self.credential_envs}

    def _acquire(self) -> str:
        while True:
            with self._lock:
                now_wall, now_mono = time.time(), time.monotonic()
                active = [n for n in self.credential_envs if self._suspended_until[n] <= now_wall]
                if active:
                    name = min(active, key=lambda n: self._next_slot[n])
                    slot = max(now_mono, self._next_slot[name])
                    self._next_slot[name] = slot + self.min_interval
                    wait = slot - now_mono
                else:
                    name, wait = None, min(self._suspended_until.values()) - now_wall
            if name is not None:
                if wait > 0:
                    time.sleep(wait)
                return name
            print(f"[{self.model_id}] all credentials at daily quota; sleeping {wait / 3600:.2f} h", flush=True)
            time.sleep(max(30.0, min(wait, 1800.0)))

    def _redact(self, body: bytes) -> bytes:
        for name in self.credential_envs:
            secret = os.environ.get(name)
            if secret:
                body = body.replace(secret.encode("utf-8"), b"[REDACTED]")
        return body

    def __call__(self, endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
        transient = 0
        while True:
            name = self._acquire()
            secret = os.environ.get(name)
            if not secret:
                raise TimeoutError("credential variable not set")
            sent_headers = {**headers, "Authorization": f"Bearer {secret}"}
            started = _utc_now()
            try:
                response = _http_post_json(endpoint, sent_headers, body, timeout)
            except (TimeoutError, OSError) as exc:
                status, retry_after, kind, response = None, None, type(exc).__name__, None
            else:
                response = HttpResponse(response.status_code, self._redact(response.body), response.request_id, response.retry_after)
                status, retry_after, kind = response.status_code, response.retry_after, "http_status"
            self.credential_log.append({
                "record_type": "credential_request", "at_utc": started, "model_id": self.model_id,
                "credential_variable": name, "trial_id": getattr(_context, "trial_id", None),
                "trial_attempt": getattr(_context, "attempt", None), "status_code": status,
                "exception_type": None if kind == "http_status" else kind,
                "request_body_sha256": hashlib.sha256(body).hexdigest(),
            })
            if response is not None and status == 429 and any(m in response.body for m in DAILY_QUOTA_MARKERS):
                with self._lock:
                    self._suspended_until[name] = _next_daily_reset_epoch()
                self.events.append({
                    "record_type": "credential_suspended_daily_quota", "at_utc": _utc_now(), "model_id": self.model_id,
                    "credential_variable": name,
                    "until_utc": datetime.fromtimestamp(self._suspended_until[name], timezone.utc).isoformat(),
                })
                continue
            if response is not None and (status not in TRANSIENT_STATUS or any(m in response.body for m in NON_TRANSIENT_MARKERS)):
                return response
            if transient >= MAX_POOL_TRANSIENT_RETRIES:
                if response is None:
                    raise TimeoutError("transport retries exhausted")
                return response
            transient += 1
            backoff = min(120.0, 4.0 * (2 ** (transient - 1))) + random.uniform(0, 2)
            try:
                if retry_after is not None:
                    backoff = max(backoff, float(retry_after))
            except ValueError:
                pass
            if status == 429:
                with self._lock:
                    self._next_slot[name] = max(self._next_slot[name], time.monotonic() + backoff)
                backoff = 0.5  # another pooled credential may be available immediately
            self.events.append({
                "record_type": "transport_retry_event", "at_utc": _utc_now(), "model_id": self.model_id,
                "credential_variable": name, "trial_id": getattr(_context, "trial_id", None),
                "trial_attempt": getattr(_context, "attempt", None), "status_code": status,
                "exception_type": None if kind == "http_status" else kind, "retry_after": retry_after,
                "transport_attempt": transient, "backoff_seconds": round(backoff, 3),
                "request_body_sha256": hashlib.sha256(body).hexdigest(),
            })
            time.sleep(backoff)


@dataclass(frozen=True, slots=True)
class PlannedTrial:
    identity: TrialIdentity
    scenario: ResearchScenario


def plan_trials(
    model_config: ModelConfig,
    scenarios: tuple[ResearchScenario, ...],
    goals: tuple[str, ...],
    marketings: tuple[str, ...],
    repetitions: tuple[int, ...],
    experiment_version: str,
    code_revision: str,
    variant: ProtocolVariant = CORE_VARIANT,
) -> tuple[PlannedTrial, ...]:
    planned = []
    for scenario in scenarios:
        config_sha = live_trial_config_sha256(model_config, scenario.config.config_sha256, experiment_version, variant)
        for goal in goals:
            template_id = generate_request(scenario.objective, GoalCondition(goal), template_index=variant.template_index).template_id
            for marketing in marketings:
                for repetition in repetitions:
                    seed_material = f"{experiment_version}|{scenario.scenario_id}|{goal}|{marketing}|{model_config.model_id}|{repetition}"
                    seed = int.from_bytes(hashlib.sha256(seed_material.encode()).digest()[:4], "big")
                    planned.append(PlannedTrial(
                        TrialIdentity(
                            scenario_id=scenario.scenario_id,
                            profile_id=scenario.objective.objective_id,
                            goal_condition=goal,
                            marketing_condition=marketing,
                            model_family=model_config.model_family,
                            model_version=model_config.model_id,
                            repetition=repetition,
                            prompt_template_id=template_id,
                            experiment_version=experiment_version,
                            config_sha256=config_sha,
                            random_seed=seed,
                            code_revision=code_revision,
                        ),
                        scenario,
                    ))
    return tuple(planned)


class ModelBatchRunner:
    """Runs one model's planned trials into one run directory."""

    def __init__(
        self,
        run_dir: Path,
        model_config: ModelConfig,
        planned: tuple[PlannedTrial, ...],
        *,
        min_interval_seconds: float,
        workers: int = 1,
        max_trials: int | None = None,
        progress_every: int = 20,
        variant: ProtocolVariant = CORE_VARIANT,
        credential_envs: tuple[str, ...] | None = None,
    ) -> None:
        self.variant = variant
        if not planned:
            raise ValueError("No planned trials.")
        self.run_dir = run_dir / _safe_name(model_config.model_id)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.model_config = model_config
        self.planned = {trial.identity.trial_id: trial for trial in planned}
        config_shas = {trial.identity.config_sha256 for trial in planned}
        if len(config_shas) != 1:
            raise ValueError("A model batch must share one config digest.")
        self.checkpoint = CheckpointStore(self.run_dir / "checkpoint.sqlite", config_shas.pop())
        self.checkpoint.register_trials(trial.identity for trial in planned)
        self.checkpoint.requeue_interrupted()
        self.events = _LockedJsonl(self.run_dir / "transport_events.jsonl")
        self.runner_events = _LockedJsonl(self.run_dir / "runner_events.jsonl")
        if credential_envs:
            self.transport = CredentialPoolTransport(
                credential_envs, min_interval_seconds, self.events,
                _LockedJsonl(self.run_dir / "credential_requests.jsonl"), model_config.model_id,
            )
        else:
            self.transport = ThrottledTransport(min_interval_seconds, self.events, model_config.model_id)
        self.adapter = make_adapter(model_config, self.transport)
        self.workers = workers
        self.max_trials = max_trials
        self.progress_every = progress_every
        self._locks = {name: threading.Lock() for name in ("trace", "raw", "fail")}
        self._loggers: dict[int, tuple] = {}
        self._done = 0
        self._count_lock = threading.Lock()

    def _loggers_for(self, attempt: int):
        if attempt not in self._loggers:
            self._loggers[attempt] = (
                _LockedTrace(self.run_dir / f"traces.attempt{attempt}.jsonl", self._locks["trace"]),
                _LockedRawIO(self.run_dir / f"model_io.attempt{attempt}.jsonl", self._locks["raw"]),
                _LockedFailures(self.run_dir / "failures.jsonl", self._locks["fail"]),
            )
        return self._loggers[attempt]

    def _run_one(self, trial_id: str) -> None:
        trial = self.planned[trial_id]
        record = self.checkpoint.get(trial_id)
        attempt = record.attempt_count + 1
        traces, raw, failures = self._loggers_for(attempt)
        _context.trial_id, _context.attempt = trial_id, attempt
        controller = LiveTrialController(self.adapter, self.checkpoint, traces, raw, failures, self.variant)
        result = controller.run(trial.identity, trial.scenario)
        self.runner_events.append({
            "record_type": "trial_attempt_finished",
            "at_utc": _utc_now(),
            "trial_id": trial_id,
            "attempt": attempt,
            "completed": result.completed,
            "failure_category": result.failure.category.value if result.failure else None,
            "failure_stage": result.failure.stage if result.failure else None,
        })
        if (
            not result.completed
            and result.failure is not None
            and result.failure.stage == "model_api"
            and result.failure.category.value in TECHNICAL_RETRY_CATEGORIES
            and attempt == 1
        ):
            self.checkpoint.requeue_failed(trial_id, TECHNICAL_RETRY_REASON)
            self.runner_events.append({
                "record_type": "technical_retry_scheduled",
                "at_utc": _utc_now(),
                "trial_id": trial_id,
                "original_failure_category": result.failure.category.value,
                "reason": TECHNICAL_RETRY_REASON,
            })
            self._run_one(trial_id)
            return
        with self._count_lock:
            self._done += 1
            if self._done % self.progress_every == 0:
                print(f"[{self.model_config.model_id}] finished {self._done} trials", flush=True)

    def run(self) -> dict[str, object]:
        pending = [trial_id for trial_id in self.checkpoint.pending_trial_ids() if trial_id in self.planned]
        # Deterministic but interleaved execution order across cells.
        pending.sort(key=lambda trial_id: hashlib.sha256(trial_id.encode()).hexdigest())
        if self.max_trials is not None:
            pending = pending[: self.max_trials]
        if self.workers <= 1:
            for trial_id in pending:
                self._run_one(trial_id)
        else:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                list(pool.map(self._run_one, pending))
        return self.status()

    def status(self) -> dict[str, object]:
        counts: dict[str, int] = {}
        for record in self.checkpoint.list_records():
            counts[record.status.value] = counts.get(record.status.value, 0) + 1
        return {"model_id": self.model_config.model_id, "status_counts": counts, "planned": len(self.planned)}


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-._" else "_" for char in value)
