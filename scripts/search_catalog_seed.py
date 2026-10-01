"""Restricted-randomization catalog seed search under catalog-acceptance-v1.0.0.

Seeds are tried in order base, base+1, ... ; the first catalog passing every
pre-specified criterion is accepted. The attribute generator, objective seed and
cue seed are unchanged. Writes configs/core_v2.json (Phase-1 config preserved)
and artifacts/environment_seed_search.json.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.catalog import generate_catalog  # noqa: E402
from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.environment_diagnostics import ACCEPTANCE_VERSION, MAX_SEED_SEARCH, evaluate_environment  # noqa: E402
from before_recommendation.objectives import generate_objectives  # noqa: E402


def main() -> None:
    base_path = ROOT / "configs" / "phase1.json"
    base = load_phase1_config(base_path)
    objectives = generate_objectives(base)
    failures: Counter[str] = Counter()
    accepted = None
    for offset in range(MAX_SEED_SEARCH):
        seed = base.catalog_seed + offset
        report = evaluate_environment(generate_catalog(base, seed=seed), objectives, base)
        if report.passed:
            accepted = (seed, offset, report)
            break
        failures.update(name for name, check in report.checks.items() if not check["pass"])
    if accepted is None:
        raise SystemExit("No seed satisfied the criteria within the search bound.")
    seed, offset, report = accepted

    payload = json.loads(base_path.read_text(encoding="utf-8"))
    payload["experiment_version"] = "core-v2.0.0"
    payload["seeds"]["catalog"] = seed
    payload["catalog_acceptance"] = {
        "version": ACCEPTANCE_VERSION,
        "base_catalog_seed": base.catalog_seed,
        "seeds_rejected_before_acceptance": offset,
        "accepted_catalog_seed": seed,
        "supersedes_config": "configs/phase1.json (preserved unchanged)",
    }
    out_config = ROOT / "configs" / "core_v2.json"
    out_config.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    v2 = load_phase1_config(out_config)
    final = evaluate_environment(generate_catalog(v2), generate_objectives(v2), v2)
    assert final.passed and final.optimal_counts == report.optimal_counts

    phase1_report = evaluate_environment(generate_catalog(base), objectives, base)
    artifact = {
        "artifact_version": "environment-seed-search-v1",
        "acceptance_version": ACCEPTANCE_VERSION,
        "procedure": "deterministic seed order base, base+1, ...; first catalog passing all pre-specified criteria accepted",
        "base_seed": base.catalog_seed,
        "accepted_seed": seed,
        "seeds_rejected": offset,
        "rejection_reason_counts": dict(failures.most_common()),
        "phase1_catalog_report": phase1_report.as_dict(),
        "accepted_catalog_report": final.as_dict(),
        "core_v2_config_sha256": v2.config_sha256,
        "phase1_config_sha256": base.config_sha256,
    }
    (ROOT / "artifacts" / "environment_seed_search.json").write_text(json.dumps(artifact, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"accepted_seed": seed, "rejected": offset, "optima": final.optimal_counts,
                      "checks": {k: v["value"] for k, v in final.checks.items() if k != "distinct_class_modal_optima"}}, indent=1, default=str))


if __name__ == "__main__":
    main()
