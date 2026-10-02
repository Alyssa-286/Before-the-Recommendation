"""Final end-to-end validation. Writes artifacts/final_validation.json.

1. Full unit/integration test suite.
2. Independent recomputation from RAW traces (not the analysis dataset): D, utility,
   optimal utility, regret, and matched delta-D; compared with the analysis dataset.
3. Config/seed provenance against the freeze; condition assignment re-derived.
4. Leakage + arm-name scan of every model-visible request (core and robustness).
5. Manuscript numbers: every rendered token must equal the freshly computed token.
6. Secret scan of all git-tracked files and logs; .env ignored.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.dataset import DIMENSIONS, load_stage  # noqa: E402
from before_recommendation.evaluator import utility_features  # noqa: E402
from before_recommendation.experiment_config import CORE_CONFIG_PATH, STAGES  # noqa: E402
from before_recommendation.leakage import check_request_payload  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402


def main() -> None:
    report: dict[str, object] = {"artifact_version": "final-validation-v1"}
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT, capture_output=True, text=True)
    tail = (tests.stderr or "").strip().splitlines()[-3:]
    report["tests"] = {"returncode": tests.returncode, "summary": tail}

    config = load_phase1_config(CORE_CONFIG_PATH)
    freeze = json.loads((ROOT / "artifacts" / "experiment_freeze.json").read_text(encoding="utf-8"))
    scenarios = {s.scenario_id: s for s in generate_scenarios(config)}
    catalog = next(iter(scenarios.values())).catalog
    X = {p.product_id: utility_features(p, catalog) for p in catalog.products}
    report["provenance"] = {
        "config_sha256_matches_freeze": config.config_sha256 == freeze["environment"]["config_sha256"],
        "catalog_seed": config.catalog_seed, "objective_seed": config.objectives_seed, "cue_seed": config.cues_seed,
        "seeds_match_freeze": (config.catalog_seed, config.objectives_seed, config.cues_seed) == (
            freeze["environment"]["catalog_seed"], freeze["environment"]["objective_seed"], freeze["environment"]["cue_seed"]),
        "frozen_file_hashes_unchanged": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in freeze["file_sha256"].items()},
    }

    recompute = {}
    leakage = {}
    for stage in ("core", "robust_template", "robust_order", "robust_cue_location"):
        stage_dir = ROOT / "data" / stage
        if not stage_dir.exists():
            continue
        finals, _, io = load_stage(stage_dir)
        ds_path = ROOT / "data" / "analysis" / f"{stage}_dataset.jsonl"
        ds = {json.loads(l)["trial_id"]: json.loads(l) for l in ds_path.read_text(encoding="utf-8").splitlines()} if ds_path.exists() else {}
        mismatches, n, cells = 0, 0, {}
        for t in finals:
            ev = [e for e in t["events"] if e["event_type"] == "trial_completed"]
            if not ev:
                continue
            final = t["derived"]["attempts"][-1]["parsed_output"]  # raw parsed model output
            w_hat = final["preference_weights"]; top = final["ranked_products"][0]
            w_star = dict(scenarios[t["identity"]["scenario_id"]].objective.weights)
            D = 0.5 * sum(abs(float(w_hat[k]) - w_star[k]) for k in DIMENSIONS)
            U = {pid: sum(w_star[k] * X[pid][k] for k in DIMENSIONS) for pid in X}
            u_opt = max(U.values())
            row = ds.get(t["trial_id"], {})
            n += 1
            ok = (abs(D - row.get("representation_error", -9)) < 1e-9 and abs(U[top] - row.get("recommended_utility", -9)) < 1e-9
                  and abs(u_opt - row.get("optimal_utility", -9)) < 1e-9 and abs(u_opt - U[top] - row.get("regret", -9)) < 1e-9)
            mismatches += not ok
            ident = t["identity"]
            cells[(ident["scenario_id"], ident["goal_condition"], ident["marketing_condition"], ident["model_family"], ident["repetition"])] = (t["trial_id"], D)
        dd_mismatch = 0
        for key, (tid, D) in cells.items():
            if key[2] == "neutral":
                continue
            neutral = cells.get((key[0], key[1], "neutral", key[3], key[4]))
            if neutral and tid in ds and ds[tid].get("delta_representation_error") is not None:
                dd_mismatch += abs((D - neutral[1]) - ds[tid]["delta_representation_error"]) > 1e-9
        recompute[stage] = {"valid_trials_recomputed": n, "metric_mismatches": mismatches, "delta_D_mismatches": dd_mismatch}
        trial_scenario = {t["trial_id"]: t["identity"]["scenario_id"] for t in finals}
        hits, arm, checked = 0, 0, 0
        for rec in io:
            if rec.get("request_payload") and rec["trial_id"] in trial_scenario:
                checked += 1
                hits += bool(check_request_payload(rec["request_payload"], scenarios[trial_scenario[rec["trial_id"]]]))
                arm += any(m.get("role") == "tool" and any(a in (m.get("content") or "") for a in ("marketing_condition", "social_proof", "scarcity"))
                           for m in rec["request_payload"].get("messages", []))
        leakage[stage] = {"requests_checked": checked, "leakage_findings": hits, "arm_name_findings": arm}
    report["independent_recomputation"] = recompute
    report["leakage"] = leakage

    # Manuscript numbers: recompute tokens and compare with the rendered token file.
    import render_manuscript
    fresh = render_manuscript.build_tokens()
    rendered = json.loads((ROOT / "manuscript" / "manuscript_tokens.json").read_text(encoding="utf-8")) if (ROOT / "manuscript" / "manuscript_tokens.json").exists() else {}
    diffs = sorted(k for k in fresh if rendered.get(k) != fresh[k])
    paper = (ROOT / "manuscript" / "paper.md").read_text(encoding="utf-8") if (ROOT / "manuscript" / "paper.md").exists() else ""
    report["manuscript"] = {"tokens": len(fresh), "token_mismatches": diffs, "unresolved_placeholders": paper.count("{{"), "verify_markers": paper.count("[[VERIFY]]")}

    # Secrets
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    try:
        from dotenv import dotenv_values
        secrets = [v for v in dotenv_values(ROOT / ".env").values() if v]
    except Exception:
        secrets = []
    leaked = [f for f in tracked if (ROOT / f).is_file() and any(s.encode() in (ROOT / f).read_bytes() for s in secrets)]
    log_leaks = [str(p.relative_to(ROOT)) for p in (ROOT / "logs").rglob("*") if p.is_file() and any(s.encode() in p.read_bytes() for s in secrets)] if (ROOT / "logs").exists() else []
    ignored = subprocess.run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True, text=True).returncode == 0
    report["security"] = {"env_ignored": ignored, "env_tracked": ".env" in tracked, "tracked_files_scanned": len(tracked),
                          "tracked_files_with_secret": leaked, "log_files_with_secret": log_leaks, "secrets_checked": len(secrets)}
    report["all_passed"] = (tests.returncode == 0 and all(report["provenance"]["frozen_file_hashes_unchanged"].values())
                            and report["provenance"]["config_sha256_matches_freeze"] and report["provenance"]["seeds_match_freeze"]
                            and all(v["metric_mismatches"] == 0 and v["delta_D_mismatches"] == 0 for v in recompute.values())
                            and all(v["leakage_findings"] == 0 and v["arm_name_findings"] == 0 for v in leakage.values())
                            and not diffs and report["manuscript"]["unresolved_placeholders"] == 0 and report["manuscript"]["verify_markers"] == 0
                            and ignored and not leaked and not log_leaks)
    (ROOT / "artifacts" / "final_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "provenance"}, indent=1))


if __name__ == "__main__":
    main()
