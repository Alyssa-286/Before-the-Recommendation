"""Infrastructure-only selection probe of free Mistral models (NOT research data).

Both candidates cost INR 0 on the Mistral Free mode, so the frozen tie-breaker is
protocol reliability. 4 trials each on SCENARIO_006 (ambiguous/explicit x neutral/discount).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.dataset import build_rows  # noqa: E402
from before_recommendation.experiment_config import CORE_CONFIG_PATH  # noqa: E402
from before_recommendation.experiment_runner import ModelBatchRunner, current_code_revision, plan_trials  # noqa: E402
from before_recommendation.leakage import check_request_payload  # noqa: E402
from before_recommendation.model_adapters import ModelConfig  # noqa: E402
from before_recommendation.runtime_config import load_runtime_environment  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402
from before_recommendation.dataset import read_jsonl  # noqa: E402

COMMON = dict(temperature=None, max_output_tokens=4096, timeout_seconds=120.0)
CANDIDATES = {
    "ministral-14b-2512": ModelConfig("mistral_chat_completions", "ministral-14b-2512", "mistral", "MISTRAL_API_KEY", **COMMON),
    "ministral-8b-2512": ModelConfig("mistral_chat_completions", "ministral-8b-2512", "mistral", "MISTRAL_API_KEY", **COMMON),
}


def main() -> None:
    load_runtime_environment(names=("MISTRAL_API_KEY",))
    revision = current_code_revision(ROOT)
    scenarios = {s.scenario_id: s for s in generate_scenarios(load_phase1_config(CORE_CONFIG_PATH))}
    run_dir = ROOT / "data" / "mistral_selection_probe"
    summary = {"artifact_version": "mistral-selection-probe-v1", "purpose": "infrastructure-only; not research data", "code_revision": revision, "candidates": {}}
    for name, config in CANDIDATES.items():
        planned = plan_trials(config, (scenarios["SCENARIO_006"],), ("ambiguous", "explicit"), ("neutral", "discount"), (1,), "mistral-selection-probe-v1", revision)
        runner = ModelBatchRunner(run_dir, config, planned, min_interval_seconds=2.5, credential_envs=("MISTRAL_API_KEY",))
        status = runner.run()
        model_dir = runner.run_dir
        rows = [r for r in build_rows(run_dir, scenarios) if r["model_version"] == config.model_id]
        io = [r for a in (1, 2) for r in read_jsonl(model_dir / f"model_io.attempt{a}.jsonl")]
        leaks = sum(bool(check_request_payload(r["request_payload"], scenarios["SCENARIO_006"])) for r in io if r.get("request_payload"))
        summary["candidates"][name] = {
            "status": status["status_counts"], "valid": sum(r["valid"] for r in rows), "trials": len(rows),
            "failures": [(r["terminal_failure_category"], r["terminal_failure_detail"]) for r in rows if not r["valid"]],
            "parser_retries": sum(r["parser_retry_used"] for r in rows), "clarifications": sum(r["clarification"] for r in rows),
            "tokens_per_trial": sum(r["input_tokens"] + r["output_tokens"] for r in rows) / max(1, len(rows)),
            "observed_model_ids": sorted({m for r in rows for m in r["observed_model_ids"]}), "leakage_findings": leaks,
        }
        print(name, json.dumps(summary["candidates"][name]), flush=True)
    (ROOT / "artifacts" / "mistral_selection_probe.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
