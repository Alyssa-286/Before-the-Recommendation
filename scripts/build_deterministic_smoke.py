"""Write a reproducible, non-experimental snapshot of the deterministic layer."""

from __future__ import annotations

import json
from pathlib import Path
import platform
import subprocess

from before_recommendation.catalog import CATALOG_GENERATOR_VERSION, catalog_fingerprint
from before_recommendation.conditions import (
    CUE_GENERATOR_VERSION,
    check_factual_utility_balance,
    generate_cue_arms,
)
from before_recommendation.config import load_phase1_config
from before_recommendation.evaluator import score_catalog
from before_recommendation.objectives import OBJECTIVE_GENERATOR_VERSION
from before_recommendation.prompts import PROMPT_GENERATOR_VERSION, GoalCondition, generate_request
from before_recommendation.scenarios import SCENARIO_GENERATOR_VERSION, generate_scenarios
from before_recommendation.simulated_user import (
    SIMULATED_USER_VERSION,
    SUPPORTED_TARGETS,
    answer_clarification,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "artifacts" / "phase1_deterministic_smoke.json"


def _source_revision() -> str | None:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "rev-parse",
            "--verify",
            "HEAD",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def build_report() -> dict[str, object]:
    config = load_phase1_config()
    scenarios = generate_scenarios(config)
    repeated_scenarios = generate_scenarios(config)
    example = scenarios[0]
    evaluation = score_catalog(example.objective, example.catalog)
    arms = generate_cue_arms(example.catalog, config)
    balance_reports = tuple(
        check_factual_utility_balance(scenario.objective, scenario.catalog, arms)
        for scenario in scenarios
    )

    cue_summary = {}
    for arm in arms:
        cue_summary[arm.condition.value] = {
            "cued_product_ids": list(arm.cued_product_ids),
            "labels": sorted(
                {listing.marketing_label for listing in arm.listings if listing.marketing_label}
            ),
            "labeled_product_count": sum(listing.marketing_label is not None for listing in arm.listings),
        }

    optimal = example.catalog.get(evaluation.optimal_product_id)
    example_balance = balance_reports[0]
    source_revision = _source_revision()
    return {
        "artifact_type": "deterministic_foundation_smoke",
        "interpretation": "Synthetic implementation validation only; no agent calls or experiment data.",
        "runtime": {"python": platform.python_version(), "source_revision": source_revision},
        "versions": {
            "experiment": config.experiment_version,
            "config_schema": config.schema_version,
            "catalog_generator": CATALOG_GENERATOR_VERSION,
            "objective_generator": OBJECTIVE_GENERATOR_VERSION,
            "prompt_generator": PROMPT_GENERATOR_VERSION,
            "simulated_user": SIMULATED_USER_VERSION,
            "cue_generator": CUE_GENERATOR_VERSION,
            "scenario_generator": SCENARIO_GENERATOR_VERSION,
        },
        "config_sha256": config.config_sha256,
        "seeds": {
            "catalog": config.catalog_seed,
            "objectives": config.objectives_seed,
            "cues": config.cues_seed,
        },
        "reproduction": {
            "scenario_count": len(scenarios),
            "catalog_product_count": len(example.catalog.products),
            "repeat_generation_equal": scenarios == repeated_scenarios,
            "catalog_fingerprint": catalog_fingerprint(example.catalog),
        },
        "example_scenario": {
            "scenario_id": example.scenario_id,
            "profile_class": example.objective.profile_class,
            "controlled_objective_weights": example.objective.as_dict(),
            "hard_max_price_inr": example.objective.hard_max_price_inr,
            "soft_budget_reference_inr": example.objective.budget_reference_inr,
            "requests": {
                condition.value: generate_request(example.objective, condition).text
                for condition in GoalCondition
            },
            "optimal_product": {
                "product_id": optimal.product_id,
                "price_inr": optimal.price_inr,
                "utility": evaluation.optimal_utility,
                "feasible": evaluation.is_feasible(optimal.product_id),
            },
            "simulated_user_answers": {
                target: answer_clarification(example.objective, target).answer
                for target in SUPPORTED_TARGETS
            },
            "unsupported_target_answer": answer_clarification(
                example.objective, "repairability"
            ).answer,
        },
        "cue_conditions": cue_summary,
        "factual_utility_balance": {
            "all_40_objectives_balanced": all(report.balanced for report in balance_reports),
            "maximum_per_product_utility_difference": max(
                report.max_per_product_utility_difference for report in balance_reports
            ),
            "condition_mean_utility": {
                condition: mean for condition, mean in example_balance.condition_means
            },
            "same_factual_records_in_all_arms": all(
                report.factual_records_match_catalog for report in balance_reports
            ),
        },
        "source_revision_note": (
            f"Generated from Git commit {source_revision}."
            if source_revision
            else "No Git commit exists at generation time; capture one before experiment freeze."
        ),
    }


if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(build_report(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_PATH)
