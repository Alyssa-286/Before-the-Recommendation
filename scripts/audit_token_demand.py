"""Observed token demand from the live pilot, per model, goal x marketing arm and call index.

Reads preserved pilot traces/raw I/O only (no API calls). Writes
artifacts/token_demand_audit.json.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.dataset import read_jsonl  # noqa: E402


def _mean(values):
    values = list(values)
    return round(statistics.mean(values), 1) if values else None


def main() -> None:
    stage = ROOT / "data" / "pilot"
    out: dict[str, object] = {"artifact_version": "token-demand-audit-v1", "source": "data/pilot (32-run live pilot, controller v1.0.0, Phase-1 catalog)", "models": {}}
    for model_dir in sorted(p for p in stage.iterdir() if p.is_dir()):
        traces = {t["trial_id"]: t for a in (1, 2) for t in read_jsonl(model_dir / f"traces.attempt{a}.jsonl")}
        io = [r for a in (1, 2) for r in read_jsonl(model_dir / f"model_io.attempt{a}.jsonl")]
        ok = [r for r in io if r["record_type"] == "model_io"]
        per_trial = defaultdict(lambda: {"in": 0, "out": 0, "calls": 0})
        by_call = defaultdict(lambda: {"in": [], "out": []})
        payload_chars = defaultdict(list)
        for r in ok:
            pt = per_trial[r["trial_id"]]
            pt["in"] += r.get("input_tokens") or 0
            pt["out"] += r.get("output_tokens") or 0
            pt["calls"] += 1
            by_call[r["call_index"]]["in"].append(r.get("input_tokens") or 0)
            by_call[r["call_index"]]["out"].append(r.get("output_tokens") or 0)
            msgs = r["request_payload"]["messages"]
            payload_chars["system"].append(sum(len(m.get("content") or "") for m in msgs if m["role"] == "system"))
            payload_chars["tool_definitions_json"].append(len(json.dumps(r["request_payload"].get("tools"))))
            tool_msgs = [m for m in msgs if m["role"] == "tool"]
            if tool_msgs:
                payload_chars["catalog_tool_result"].append(len(tool_msgs[0]["content"]))
        arms = defaultdict(list)
        for tid, t in traces.items():
            ident = t["identity"]
            arms[f"{ident['goal_condition']}|{ident['marketing_condition']}"].append(per_trial[tid])
        valid = sum(1 for t in traces.values() if t["events"] and t["events"][-1]["event_type"] == "trial_completed")
        retries = sum(1 for t in traces.values() for e in t["events"] if e["event_type"] == "parser_retry_requested")
        retry_calls_in = sum(r.get("input_tokens") or 0 for r in ok
                             if any(e["event_type"] == "parser_retry_requested" for e in traces[r["trial_id"]]["events"])
                             and r["call_index"] == max(x["call_index"] for x in ok if x["trial_id"] == r["trial_id"]))
        totals_in = [v["in"] for v in per_trial.values()]
        totals_out = [v["out"] for v in per_trial.values()]
        out["models"][model_dir.name] = {
            "trials": len(traces), "valid": valid, "valid_rate": valid / len(traces),
            "parser_retries": retries,
            "input_tokens_per_trial_mean": _mean(totals_in), "output_tokens_per_trial_mean": _mean(totals_out),
            "input_share_of_total": round(sum(totals_in) / (sum(totals_in) + sum(totals_out)), 3),
            "calls_per_trial_mean": _mean(v["calls"] for v in per_trial.values()),
            "tokens_by_call_index": {str(k): {"input_mean": _mean(v["in"]), "output_mean": _mean(v["out"]), "n": len(v["in"])} for k, v in sorted(by_call.items())},
            "input_tokens_in_final_retry_calls_total": retry_calls_in,
            "by_arm": {k: {"n": len(v), "input_mean": _mean(x["in"] for x in v), "output_mean": _mean(x["out"] for x in v), "calls_mean": _mean(x["calls"] for x in v)} for k, v in sorted(arms.items())},
            "request_component_chars_mean": {k: _mean(v) for k, v in payload_chars.items()},
        }
    (ROOT / "artifacts" / "token_demand_audit.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
