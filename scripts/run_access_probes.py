"""Infrastructure-only live access probes (NOT research observations).

Runs two protocol trials per candidate model into ``data/access_probes/`` and
summarizes access, identity, tool/parse compatibility, usage, latency and
leakage into ``artifacts/live_access_probe.json``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.experiment_runner import ModelBatchRunner, current_code_revision, plan_trials  # noqa: E402
from before_recommendation.leakage import check_request_payload  # noqa: E402
from before_recommendation.model_adapters import ModelConfig  # noqa: E402
from before_recommendation.runtime_config import load_runtime_environment  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402


COMMON = dict(temperature=None, max_output_tokens=4096, timeout_seconds=120.0)
CANDIDATES = {
    "gpt-5-nano": ModelConfig("openai_chat_completions", "gpt-5-nano-2025-08-07", "openai_gpt", "OPENAI_API_KEY", reasoning_effort="minimal", **COMMON),
    "gpt-4.1-nano": ModelConfig("openai_chat_completions", "gpt-4.1-nano-2025-04-14", "openai_gpt", "OPENAI_API_KEY", **COMMON),
    "gemini-2.5-flash-lite": ModelConfig("gemini_openai_compat", "gemini-2.5-flash-lite", "google_gemini", "GEMINI_API_KEY", **COMMON),
    "gemini-3.1-flash-lite": ModelConfig("gemini_openai_compat", "gemini-3.1-flash-lite", "google_gemini", "GEMINI_API_KEY", **COMMON),
    "gemma-4-26b-a4b-it": ModelConfig("gemini_openai_compat", "gemma-4-26b-a4b-it", "google_gemma", "GEMINI_API_KEY", **COMMON),
    "groq-gpt-oss-20b": ModelConfig("groq_chat_completions", "openai/gpt-oss-20b", "openai_gpt_oss", "GROQ_API_KEY", reasoning_effort="low", **COMMON),
    "groq-qwen3.8-27b": ModelConfig("groq_chat_completions", "qwen/qwen3.8-27b", "alibaba_qwen", "GROQ_API_KEY", **COMMON),
}
PROBE_CELLS = (("SCENARIO_001", "ambiguous", "neutral"), ("SCENARIO_002", "explicit", "discount"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(name: str, config: ModelConfig, run_dir: Path, scenarios_by_id: dict) -> dict:
    model_dir = run_dir / "".join(c if c.isalnum() or c in "-._" else "_" for c in config.model_id)
    traces = [row for attempt in (1, 2) for row in _read_jsonl(model_dir / f"traces.attempt{attempt}.jsonl")]
    io = [row for attempt in (1, 2) for row in _read_jsonl(model_dir / f"model_io.attempt{attempt}.jsonl")]
    transport = _read_jsonl(model_dir / "transport_events.jsonl")
    leakage = []
    for row in io:
        trace = next((t for t in traces if t["trial_id"] == row["trial_id"]), None)
        if trace and row.get("request_payload"):
            scenario = scenarios_by_id[trace["identity"]["scenario_id"]]
            hits = check_request_payload(row["request_payload"], scenario)
            if hits:
                leakage.append({"trial_id": row["trial_id"], "call_index": row["call_index"], "findings": hits})
    completed = [t for t in traces if t.get("derived_metrics", {}).get("recommendation_submitted") and not t.get("failures") or
                 any(e["event_type"] == "trial_completed" for e in t.get("events", []))]
    ok_io = [r for r in io if r["record_type"] == "model_io"]
    in_tok = [r["input_tokens"] for r in ok_io if isinstance(r.get("input_tokens"), int)]
    out_tok = [r["output_tokens"] for r in ok_io if isinstance(r.get("output_tokens"), int)]
    trials = []
    for t in traces:
        events = t.get("events", [])
        trials.append({
            "trial_id": t["trial_id"],
            "goal": t["identity"]["goal_condition"],
            "marketing": t["identity"]["marketing_condition"],
            "completed": any(e["event_type"] == "trial_completed" for e in events),
            "event_sequence": [f"{e['actor']}:{e['event_type']}" for e in events],
            "failures": t.get("failures", []),
            "clarification_needed": t.get("derived_metrics", {}).get("clarification_needed"),
            "question_target": t.get("derived_metrics", {}).get("question_target"),
            "provider_calls": sum(1 for r in io if r["trial_id"] == t["trial_id"]),
        })
    failures_io = [
        {"call_index": r["call_index"], "status": r.get("response_status"), "category": r.get("failure_category"),
         "detail": r.get("detail_code"), "body_preview": (r.get("raw_response_text") or "")[:300]}
        for r in io if r["record_type"] == "model_io_failure"
    ]
    return {
        "candidate": name,
        "configured_model_id": config.model_id,
        "model_family_label": config.model_family,
        "provider_adapter": config.provider,
        "model_config": config.public_dict(),
        "observed_model_ids": sorted({r.get("observed_model_id") for r in ok_io if r.get("observed_model_id")}),
        "trials_attempted": len(traces),
        "trials_completed": sum(1 for t in trials if t["completed"]),
        "trials": trials,
        "provider_calls_ok": len(ok_io),
        "provider_call_failures": failures_io,
        "transport_retry_events": len(transport),
        "transport_status_codes": sorted({str(e.get("status_code")) for e in transport}),
        "input_tokens_total": sum(in_tok),
        "output_tokens_total": sum(out_tok),
        "input_tokens_per_call_mean": round(statistics.mean(in_tok), 1) if in_tok else None,
        "output_tokens_per_call_mean": round(statistics.mean(out_tok), 1) if out_tok else None,
        "latency_ms_median": round(statistics.median([r["latency_ms"] for r in ok_io]), 1) if ok_io else None,
        "leakage_findings": leakage,
        "leakage_check_passed": not leakage,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()
    load_runtime_environment(names=("OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"))
    revision = current_code_revision(ROOT)
    scenarios = generate_scenarios(load_phase1_config())
    by_id = {s.scenario_id: s for s in scenarios}
    run_dir = ROOT / "data" / "access_probes"
    out_path = ROOT / "artifacts" / "live_access_probe.json"
    existing = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {"candidates": {}}
    for name, config in CANDIDATES.items():
        if args.only and name not in args.only:
            continue
        planned = []
        for scenario_id, goal, marketing in PROBE_CELLS:
            planned.extend(plan_trials(config, (by_id[scenario_id],), (goal,), (marketing,), (1,), "access-probe-v1", revision))
        runner = ModelBatchRunner(run_dir, config, tuple(planned), min_interval_seconds=4.0)
        status = runner.run()
        summary = summarize(name, config, run_dir, by_id)
        summary["checkpoint_status"] = status
        summary["code_revision"] = revision
        existing["candidates"][name] = summary
        print(name, status["status_counts"], "leak_ok" if summary["leakage_check_passed"] else "LEAK", flush=True)
    existing.update({
        "artifact_version": "live-access-probe-v1",
        "purpose": "Infrastructure-only access probes; NOT research observations and excluded from all empirical datasets.",
        "probe_cells": [list(cell) for cell in PROBE_CELLS],
        "raw_data_directory": "data/access_probes/",
        "credential_values_recorded": False,
    })
    out_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
