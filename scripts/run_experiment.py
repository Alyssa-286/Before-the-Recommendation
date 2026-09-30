"""Run a live stage (pilot or core) for one or both selected model families.

Usage: python scripts/run_experiment.py --stage pilot [--family google_gemini] [--max-trials N]
Each family writes to data/<stage>/<model>/ with its own checkpoint; re-running
resumes from the checkpoint without repeating completed trials.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.experiment_config import GOALS, MARKETINGS, PACING, SELECTED_MODELS, STAGES  # noqa: E402
from before_recommendation.experiment_runner import ModelBatchRunner, current_code_revision, plan_trials  # noqa: E402
from before_recommendation.runtime_config import load_runtime_environment  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    parser.add_argument("--family", choices=sorted(SELECTED_MODELS), action="append")
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument("--code-revision", default=None, help="Pin to an existing checkpoint revision (resume only).")
    args = parser.parse_args()
    stage = STAGES[args.stage]
    load_runtime_environment(names=("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"))
    revision = args.code_revision or current_code_revision(ROOT)
    by_id = {s.scenario_id: s for s in generate_scenarios(load_phase1_config())}
    scenarios = tuple(by_id[scenario_id] for scenario_id in stage.scenario_ids)
    families = args.family or sorted(SELECTED_MODELS)
    results: dict[str, object] = {}

    def run_family(family: str) -> None:
        config = SELECTED_MODELS[family]
        planned = plan_trials(config, scenarios, GOALS, MARKETINGS, stage.repetitions, stage.experiment_version, revision)
        interval, workers = PACING[family]
        runner = ModelBatchRunner(ROOT / "data" / stage.name, config, planned, min_interval_seconds=interval,
                                  workers=workers, max_trials=args.max_trials)
        results[family] = runner.run()
        print(family, json.dumps(results[family]), flush=True)

    threads = [threading.Thread(target=run_family, args=(family,)) for family in families]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print(json.dumps({"stage": stage.name, "code_revision": revision, "results": results}, indent=2))


if __name__ == "__main__":
    main()
