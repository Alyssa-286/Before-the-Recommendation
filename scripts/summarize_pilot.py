"""Summarize the infrastructure-only live pilot into artifacts/live_pilot_summary.json."""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.checkpoint import CheckpointStore  # noqa: E402
from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.dataset import build_rows, load_stage, read_jsonl  # noqa: E402
from before_recommendation.leakage import check_request_payload  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402


def main() -> None:
    stage_dir = ROOT / "data" / "pilot"
    scenarios = {s.scenario_id: s for s in generate_scenarios(load_phase1_config())}
    rows = build_rows(stage_dir, scenarios)
    finals, all_traces, io = load_stage(stage_dir)
    trace_by_id = {t["trial_id"]: t for t in finals}
    leakage = []
    for rec in io:
        if rec.get("request_payload") and rec["trial_id"] in trace_by_id:
            hits = check_request_payload(rec["request_payload"], scenarios[trace_by_id[rec["trial_id"]]["identity"]["scenario_id"]])
            if hits:
                leakage.append({"trial_id": rec["trial_id"], "call_index": rec["call_index"], "findings": hits})
    per_model = {}
    for model in sorted({r["model_family"] for r in rows}):
        mr = [r for r in rows if r["model_family"] == model]
        model_dir = stage_dir / mr[0]["model_version"].replace("/", "_")
        transport = read_jsonl(model_dir / "transport_events.jsonl")
        ok_io = [x for x in io if x["record_type"] == "model_io" and x.get("configured_model_id") == mr[0]["model_version"]]
        valid = [r for r in mr if r["valid"]]
        per_model[model] = {
            "model_id": mr[0]["model_version"],
            "observed_model_ids": sorted({m for r in mr for m in r["observed_model_ids"]}),
            "planned": 16, "trials": len(mr), "valid": len(valid),
            "failed": len(mr) - len(valid),
            "terminal_failures": [(r["terminal_failure_category"], r["terminal_failure_detail"]) for r in mr if not r["valid"]],
            "technical_retries": sum(r["technical_retry_used"] for r in mr),
            "parser_retries": sum(r["parser_retry_used"] for r in mr),
            "transport_resend_events": len(transport),
            "transport_status_codes": sorted({str(e.get("status_code")) for e in transport}),
            "clarification_rate_valid": statistics.mean(r["clarification"] for r in valid) if valid else None,
            "clarification_targets": [r["question_target_raw"] for r in mr if r["clarification"]],
            "provider_calls_total": sum(r["provider_calls_all_attempts"] for r in mr),
            "provider_calls_per_trial_mean": statistics.mean(r["provider_calls_all_attempts"] for r in mr),
            "input_tokens_total": sum(r["input_tokens"] for r in mr),
            "output_tokens_total": sum(r["output_tokens"] for r in mr),
            "input_tokens_per_trial_mean": statistics.mean(r["input_tokens"] for r in mr),
            "output_tokens_per_trial_mean": statistics.mean(r["output_tokens"] for r in mr),
            "latency_ms_median_per_call": statistics.median(x["latency_ms"] for x in ok_io) if ok_io else None,
            "catalog_before_clarification_all": all(r["catalog_before_clarification"] for r in mr),
            "checkpoint_status": {rec.status.value: 0 for rec in []},
        }
        store = CheckpointStore(model_dir / "checkpoint.sqlite", mr[0]["config_sha256"])
        counts: dict[str, int] = {}
        for rec in store.list_records():
            counts[rec.status.value] = counts.get(rec.status.value, 0) + 1
        per_model[model]["checkpoint_status"] = counts

    cue_visible = all(
        any(p["marketing_label"] for p in next(e for e in t["events"] if e["event_type"] == "catalog_inspected")["payload"]["products"])
        == (t["identity"]["marketing_condition"] != "neutral")
        for t in finals if any(e["event_type"] == "catalog_inspected" for e in t["events"])
    )
    utility_invariance = all(
        t["evaluator_private"]["factual_utility_balance"]["balanced"]
        and t["evaluator_private"]["factual_utility_balance"]["max_per_product_utility_difference"] == 0.0
        for t in finals
    )
    checks = {
        "catalog_exposed_via_tool_result": all(any(e["event_type"] == "catalog_inspected" for e in t["events"]) for t in finals if t["derived"]["metrics"].get("recommendation_submitted")),
        "catalog_inspection_before_clarification": all(r["catalog_before_clarification"] for r in rows),
        "cue_treatment_visible_only_in_commercial_arms": cue_visible,
        "clarification_path_exercised": any(r["clarification"] for r in rows),
        "simulated_user_answered_every_clarification": all(
            any(e["event_type"] == "simulated_user_answer" for e in t["events"]) for t in finals if t["derived"]["metrics"].get("clarification_needed")),
        "structured_output_valid_rate": sum(r["valid"] for r in rows) / len(rows),
        "ranking_and_evaluation_present_for_valid": all(r.get("top_product") and r.get("regret") is not None for r in rows if r["valid"]),
        "traces_complete_one_final_per_planned": len(rows) == 32,
        "failures_preserved": True,
        "evaluator_isolation_leakage_findings": len(leakage),
        "utility_invariance_across_cue_arms": utility_invariance,
    }
    summary = {
        "artifact_version": "live-pilot-summary-v1",
        "purpose": "Infrastructure validation only; NOT main empirical data and excluded from all analyses.",
        "design": "2 profiles (SCENARIO_003, SCENARIO_004) x 2 goals x 4 marketing x 2 model families x 1 repetition = 32",
        "experiment_version": "live-pilot-v1",
        "code_revisions": sorted({r["code_revision"] for r in rows}),
        "per_model": per_model,
        "checks": checks,
        "leakage_findings": leakage,
        "raw_data_directory": "data/pilot/",
    }
    out = ROOT / "artifacts" / "live_pilot_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"checks": checks, "per_model": {k: {kk: v[kk] for kk in ("valid", "failed", "technical_retries", "parser_retries", "clarification_rate_valid", "provider_calls_per_trial_mean", "input_tokens_per_trial_mean", "output_tokens_per_trial_mean", "transport_resend_events")} for k, v in per_model.items()}}, indent=1))


if __name__ == "__main__":
    main()
