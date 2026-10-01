"""Write artifacts/experiment_freeze.json before any core trial is run."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation import live_controller as lc  # noqa: E402
from before_recommendation.catalog import CATALOG_GENERATOR_VERSION, catalog_fingerprint  # noqa: E402
from before_recommendation.conditions import CUE_GENERATOR_VERSION, MarketingCondition, generate_cue_arms  # noqa: E402
from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.dataset import DATASET_VERSION  # noqa: E402
from before_recommendation.environment_diagnostics import ACCEPTANCE_VERSION, evaluate_environment  # noqa: E402
from before_recommendation.experiment_config import CORE_CONFIG_PATH, CREDENTIAL_POOLS, PACING, SELECTED_MODELS, STAGES  # noqa: E402
from before_recommendation.experiment_runner import MAX_POOL_TRANSIENT_RETRIES, RUNNER_VERSION, TECHNICAL_RETRY_CATEGORIES  # noqa: E402
from before_recommendation.live_output import __name__ as _live_output  # noqa: E402,F401
from before_recommendation.model_adapters import MODEL_ADAPTER_VERSION  # noqa: E402
from before_recommendation.objectives import OBJECTIVE_GENERATOR_VERSION, generate_objectives  # noqa: E402
from before_recommendation.prompts import PROMPT_GENERATOR_VERSION, GoalCondition, generate_request  # noqa: E402
from before_recommendation.scenarios import SCENARIO_GENERATOR_VERSION, generate_scenarios, scenario_fingerprint  # noqa: E402
from before_recommendation.simulated_user import SIMULATED_USER_VERSION  # noqa: E402
from before_recommendation.statistics import BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config = load_phase1_config(CORE_CONFIG_PATH)
    scenarios = generate_scenarios(config)
    catalog = scenarios[0].catalog
    arms = generate_cue_arms(catalog, config)
    env = evaluate_environment(catalog, generate_objectives(config), config)
    core = STAGES["core"]
    pilot = json.loads((ROOT / "artifacts" / "live_pilot_v2_summary.json").read_text(encoding="utf-8"))
    tok = {fam: pilot["per_model"][fam]["input_tokens_per_trial_mean"] + pilot["per_model"][fam]["output_tokens_per_trial_mean"] for fam in SELECTED_MODELS}
    calls = {fam: pilot["per_model"][fam]["provider_calls_per_trial_mean"] for fam in SELECTED_MODELS}
    robustness_trials = sum(len(STAGES[s].scenario_ids) * len(STAGES[s].goals) * 4 for s in ("robust_template", "robust_order", "robust_cue_location"))
    capacity = {}
    for fam in SELECTED_MODELS:
        interval, workers = PACING[fam]
        rpm = len(CREDENTIAL_POOLS[fam]) * 60 / interval
        core_calls = 960 * calls[fam] * 1.10  # 10% reserve for retries/parser failures
        robust_calls = robustness_trials * calls[fam] * 1.10
        capacity[fam] = {
            "pilot_calls_per_trial": calls[fam], "pilot_tokens_per_trial": round(tok[fam], 1),
            "core_trials": 960, "core_requests_with_10pct_reserve": round(core_calls),
            "core_tokens_with_10pct_reserve": round(960 * tok[fam] * 1.10),
            "robustness_trials": robustness_trials, "robustness_requests_with_reserve": round(robust_calls),
            "paced_requests_per_minute": rpm, "core_minutes_at_pace": round(core_calls / rpm, 1),
            "credential_pool_variables": list(CREDENTIAL_POOLS[fam]),
        }
    freeze = {
        "artifact_version": "experiment-freeze-v2",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "FROZEN before any core trial; core trials pin the commit that adds this file",
        "budget": "INR 0: free routes only (Gemini FreeTier projects, Mistral Free mode); no billing, credits or upgrades",
        "design": {"scenarios": len(core.scenario_ids), "goals": list(core.goals), "marketing": [m.value for m in MarketingCondition],
                   "model_families": list(SELECTED_MODELS), "repetitions": list(core.repetitions), "planned_core_runs": 1920,
                   "experiment_version": core.experiment_version},
        "environment": {
            "config_path": "configs/core_v2.json", "config_sha256": config.config_sha256,
            "phase1_config_sha256_preserved": load_phase1_config().config_sha256,
            "catalog_seed": config.catalog_seed, "objective_seed": config.objectives_seed, "cue_seed": config.cues_seed,
            "catalog_fingerprint": catalog_fingerprint(catalog),
            "cued_product_ids": list(next(a for a in arms if a.condition is MarketingCondition.SCARCITY).cued_product_ids),
            "acceptance_version": ACCEPTANCE_VERSION, "acceptance_passed": env.passed,
            "acceptance_criteria_commit": "349e932 (committed before seed search)",
            "scenario_fingerprints_sha256": hashlib.sha256("".join(scenario_fingerprint(s) for s in scenarios).encode()).hexdigest(),
        },
        "versions": {"catalog_generator": CATALOG_GENERATOR_VERSION, "objective_generator": OBJECTIVE_GENERATOR_VERSION,
                     "cue_generator": CUE_GENERATOR_VERSION, "prompt_generator": PROMPT_GENERATOR_VERSION,
                     "scenario_generator": SCENARIO_GENERATOR_VERSION, "simulated_user": SIMULATED_USER_VERSION,
                     "live_controller": lc.LIVE_CONTROLLER_VERSION, "model_adapter": MODEL_ADAPTER_VERSION,
                     "runner": RUNNER_VERSION, "analysis_dataset": DATASET_VERSION, "analysis_plan": lc.ANALYSIS_PLAN_VERSION},
        "prompts": {
            "system_instruction": lc.LIVE_SYSTEM_INSTRUCTION,
            "core_templates": sorted({generate_request(s.objective, g, template_index=0).template_id for s in scenarios for g in GoalCondition}),
            "tools": [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in lc.LIVE_TOOLS],
        },
        "file_sha256": {p: sha(ROOT / p) for p in (
            "configs/core_v2.json", "analysis/analysis_plan.md", "schemas/agent_output.v2.schema.json",
            "src/before_recommendation/live_controller.py", "src/before_recommendation/live_output.py",
            "src/before_recommendation/evaluator.py", "src/before_recommendation/simulated_user.py",
            "src/before_recommendation/dataset.py", "src/before_recommendation/statistics.py",
            "src/before_recommendation/experiment_runner.py", "src/before_recommendation/model_adapters.py")},
        "models": {fam: {"model_config": {k: v for k, v in cfg.public_dict().items() if k != "api_key_env"},
                         "core_live_trial_config_sha256": lc.live_trial_config_sha256(cfg, config.config_sha256, core.experiment_version)}
                   for fam, cfg in SELECTED_MODELS.items()},
        "protocol_limits": {"provider_turns": lc.MAX_PROVIDER_TURNS, "parser_retries": lc.MAX_PARSER_RETRIES,
                            "clarifications": lc.MAX_CLARIFICATIONS, "tool_calls_per_response": lc.MAX_TOOL_CALLS_PER_RESPONSE},
        "retry_rules": {
            "parser": "one in-trial corrected-submission request after invalid JSON/schema; original attempt preserved",
            "technical_trial_retry": f"one full re-run (attempt 2, separate files) after terminal provider failure in {sorted(TECHNICAL_RETRY_CATEGORIES)}",
            "transport": f"HTTP 429/5xx carry no model output: per-minute 429 delays that credential, daily-quota 429 suspends it until reset, up to {MAX_POOL_TRANSIENT_RETRIES} transient re-sends; all logged",
            "never_retried": "refusals, protocol/order violations, final invalid outputs after the parser retry",
        },
        "exclusion_rules": "No outcome imputation. A run is valid only if it completes the ordered protocol with a schema-valid submission. Invalid runs remain in the manifest and denominators; scenarios lacking a needed cell are excluded only from that contrast (complete-case at scenario level, counts reported).",
        "analysis": {"plan": "analysis/analysis_plan.md v1.0.0", "bootstrap_replicates": BOOTSTRAP_REPLICATES, "bootstrap_seed": BOOTSTRAP_SEED,
                     "deviations_documented": ["catalog regenerated under catalog-acceptance-v1.0.0 (pre-data)",
                                               "model pair changed to Gemini + Mistral under the INR 0 constraint (pre-data)",
                                               "robustness datasets restricted to the ambiguous goal (primary contrast), 1 repetition (pre-data)"]},
        "robustness_stages": {name: {"experiment_version": STAGES[name].experiment_version, "variant": STAGES[name].variant.as_dict(),
                                     "goals": list(STAGES[name].goals), "trials_per_model": len(STAGES[name].scenario_ids) * len(STAGES[name].goals) * 4}
                              for name in ("robust_template", "robust_order", "robust_cue_location")},
        "capacity_plan": capacity,
        "schedule": "core first (both models in parallel, checkpointed); then robustness in plan order; analysis only after the core data-quality audit passes",
    }
    out = ROOT / "artifacts" / "experiment_freeze.json"
    out.write_text(json.dumps(freeze, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(freeze["capacity_plan"], indent=1))
    print(json.dumps(freeze["models"], indent=1))


if __name__ == "__main__":
    main()
