"""Run and compare two deterministic mock-only interface pilots."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tempfile

from before_recommendation.agent_protocol import AGENT_PROTOCOL_VERSION
from before_recommendation.analysis import build_trial_rows, summarize_trial_rows
from before_recommendation.checkpoint import CheckpointStore
from before_recommendation.conditions import MarketingCondition
from before_recommendation.config import load_phase1_config
from before_recommendation.failures import FAILURE_TAXONOMY_VERSION, JsonlFailureLogger
from before_recommendation.interface_runner import run_mock_interface_trial
from before_recommendation.mock_agent import DeterministicMockAgent, MOCK_AGENT_VERSION, MockAgentConfig
from before_recommendation.output_parser import OUTPUT_SCHEMA_VERSION
from before_recommendation.prompts import GoalCondition, PROMPT_GENERATOR_VERSION
from before_recommendation.scenarios import generate_scenarios
from before_recommendation.tracing import TRACE_SCHEMA_VERSION, JsonlTraceLogger


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "artifacts" / "phase1_interface_pilot.json"

PILOT_CASES = tuple(
    {
        "name": f"{goal.value}_{marketing.value}",
        "goal": goal,
        "marketing": marketing,
        "agent": MockAgentConfig(
            clarification_needed=goal is GoalCondition.AMBIGUOUS,
            question_target="price",
            emit_malformed_first_response=(
                goal is GoalCondition.AMBIGUOUS and marketing is MarketingCondition.DISCOUNT
            ),
        ),
    }
    for goal in GoalCondition
    for marketing in MarketingCondition
)


def _source_revision() -> str | None:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _run_once(directory: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    config = load_phase1_config()
    scenario = generate_scenarios(config)[0]
    checkpoint = CheckpointStore(directory / "checkpoint.sqlite3", config.config_sha256)
    traces = JsonlTraceLogger(directory / "traces.jsonl")
    failures = JsonlFailureLogger(directory / "failures.jsonl")

    for case in PILOT_CASES:
        run_mock_interface_trial(
            scenario,
            goal_condition=case["goal"],
            marketing_condition=case["marketing"],
            agent=DeterministicMockAgent(case["agent"]),
            checkpoint=checkpoint,
            trace_logger=traces,
            failure_logger=failures,
            model_version=MOCK_AGENT_VERSION,
        )
    return list(traces.read_all()), list(failures.read_all())


def _normalize_trace(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    normalized.pop("timestamps", None)
    return normalized


def _canonical_lines(records: list[dict[str, object]]) -> bytes:
    return ("".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    )).encode("utf-8")


def build_report() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="before-recommendation-pilot-") as first_dir:
        first_traces, first_failures = _run_once(Path(first_dir))
    with tempfile.TemporaryDirectory(prefix="before-recommendation-pilot-") as second_dir:
        second_traces, second_failures = _run_once(Path(second_dir))

    first_normalized = [_normalize_trace(record) for record in first_traces]
    second_normalized = [_normalize_trace(record) for record in second_traces]
    first_trace_bytes = _canonical_lines(first_normalized)
    second_trace_bytes = _canonical_lines(second_normalized)
    first_failure_bytes = _canonical_lines(first_failures)
    second_failure_bytes = _canonical_lines(second_failures)
    runs_identical = first_trace_bytes == second_trace_bytes and first_failure_bytes == second_failure_bytes
    if not runs_identical:
        raise RuntimeError("Two deterministic mock interface runs did not reproduce the same normalized records.")

    status_counts = Counter(
        record["derived"]["attempts"][-1]["parse_status"]
        for record in first_normalized
        if record["derived"]["attempts"]
    )
    failure_counts = Counter(row["failure"]["category"] for row in first_failures)
    run_statuses = Counter(
        "completed" if record["events"][-1]["event_type"] == "trial_completed" else "failed"
        for record in first_normalized
    )
    return {
        "artifact_type": "deterministic_interface_pilot",
        "interpretation": "Mock-only interface validation. These traces are not main-experiment data, human preferences, or evidence about shopping agents.",
        "source_revision": _source_revision(),
        "config_sha256": load_phase1_config().config_sha256,
        "versions": {
            "experiment": load_phase1_config().experiment_version,
            "agent_protocol": AGENT_PROTOCOL_VERSION,
            "mock_agent": MOCK_AGENT_VERSION,
            "prompt_generator": PROMPT_GENERATOR_VERSION,
            "output_schema": OUTPUT_SCHEMA_VERSION,
            "trace_schema": TRACE_SCHEMA_VERSION,
            "failure_taxonomy": FAILURE_TAXONOMY_VERSION,
        },
        "scope": {
            "synthetic_scenarios": 1,
            "mock_trials": len(first_normalized),
            "core_condition_cells": len(first_normalized),
            "model_families": ["deterministic_mock"],
            "repetitions_per_cell": 1,
            "external_model_calls": 0,
            "main_experiment_started": False,
            "goals_covered": sorted({record["identity"]["goal_condition"] for record in first_normalized}),
            "marketing_conditions_covered": sorted({record["identity"]["marketing_condition"] for record in first_normalized}),
        },
        "reproducibility": {
            "runs": 2,
            "normalized_traces_identical": first_trace_bytes == second_trace_bytes,
            "failure_records_identical": first_failure_bytes == second_failure_bytes,
            "normalized_traces_sha256": hashlib.sha256(first_trace_bytes).hexdigest(),
            "failure_records_sha256": hashlib.sha256(first_failure_bytes).hexdigest(),
        },
        "run_status_counts": dict(sorted(run_statuses.items())),
        "final_parse_status_counts": dict(sorted(status_counts.items())),
        "failure_counts": dict(sorted(failure_counts.items())),
        "descriptive_analysis_preview": summarize_trial_rows(build_trial_rows(first_normalized)),
        "failure_records": first_failures,
        "trial_traces": first_normalized,
    }


if __name__ == "__main__":
    report = build_report()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(
        (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(OUTPUT_PATH)
