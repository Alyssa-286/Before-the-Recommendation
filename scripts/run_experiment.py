"""Run a live stage for one or both frozen model families.

Usage: python scripts/run_experiment.py --stage core [--family mistral] [--max-trials N]
Each family writes to data/<stage>/<model>/ with its own checkpoint; re-running
resumes from the checkpoint without repeating completed trials.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.experiment_config import (  # noqa: E402
    CORE_CONFIG_PATH, CREDENTIAL_POOLS, MARKETINGS, PACING, SELECTED_MODELS, STAGES,
)
from before_recommendation.experiment_runner import ModelBatchRunner, current_code_revision, plan_trials  # noqa: E402
from before_recommendation.runtime_config import load_runtime_environment  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    parser.add_argument("--family", choices=sorted(SELECTED_MODELS), action="append")
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument("--code-revision", default=None, help="Pin to an existing checkpoint revision (resume only).")
    parser.add_argument("--extra-credential", action="append", default=[],
                        help="FAMILY=ENV_VAR: add an execution credential (same model) to a family's pool; never a new family.")
    args = parser.parse_args()
    stage = STAGES[args.stage]
    lock = ROOT / "data" / stage.name / f".runner{'.' + '+'.join(sorted(args.family)) if args.family else ''}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit(f"Another runner holds {lock}; refusing to share a checkpoint.")
    os.write(fd, str(os.getpid()).encode()); os.close(fd)
    try:
        _run(args, stage)
    finally:
        lock.unlink(missing_ok=True)


def _run(args, stage) -> None:
    pools = {fam: list(pool) for fam, pool in CREDENTIAL_POOLS.items()}
    for item in args.extra_credential:
        fam, _, env = item.partition("=")
        if fam not in pools or not env.isidentifier():
            raise SystemExit(f"Invalid --extra-credential {item!r}")
        if env not in pools[fam]:
            pools[fam].append(env)
    load_runtime_environment(names=tuple(name for pool in pools.values() for name in pool))
    revision = args.code_revision or current_code_revision(ROOT)
    by_id = {s.scenario_id: s for s in generate_scenarios(load_phase1_config(CORE_CONFIG_PATH))}
    scenarios = tuple(by_id[scenario_id] for scenario_id in stage.scenario_ids)
    families = args.family or sorted(SELECTED_MODELS)
    results: dict[str, object] = {}

    def run_family(family: str) -> None:
        config = SELECTED_MODELS[family]
        planned = plan_trials(config, scenarios, stage.goals, MARKETINGS, stage.repetitions,
                              stage.experiment_version, revision, stage.variant)
        interval, workers = PACING[family]
        runner = ModelBatchRunner(ROOT / "data" / stage.name, config, planned, min_interval_seconds=interval,
                                  workers=workers, max_trials=args.max_trials, variant=stage.variant,
                                  credential_envs=tuple(pools[family]))
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
