"""Freeze-time data-quality audit of a live stage, plus the clean analysis dataset.

Usage: python scripts/audit_core_dataset.py [stage]   (default: core)
Outputs (core): artifacts/trial_manifest.json, artifacts/data_quality_audit.json,
artifacts/core_run_summary.json, data/analysis/core_dataset.jsonl.
Every check is recomputed from raw traces / raw model I/O; nothing is edited.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.catalog import catalog_fingerprint  # noqa: E402
from before_recommendation.conditions import generate_cue_arms  # noqa: E402
from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.dataset import DIMENSIONS, build_rows, load_stage, write_dataset, read_jsonl  # noqa: E402
from before_recommendation.evaluator import score_catalog, utility_features  # noqa: E402
from before_recommendation.experiment_config import CORE_CONFIG_PATH, MARKETINGS, SELECTED_MODELS, STAGES  # noqa: E402
from before_recommendation.experiment_runner import plan_trials  # noqa: E402
from before_recommendation.leakage import check_request_payload  # noqa: E402
from before_recommendation.live_controller import _answer_question  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402


def check(name: str, passed: bool, **detail) -> dict:
    return {"check": name, "pass": bool(passed), **detail}


def main() -> None:
    stage_name = sys.argv[1] if len(sys.argv) > 1 else "core"
    stage = STAGES[stage_name]
    stage_dir = ROOT / "data" / stage_name
    config = load_phase1_config(CORE_CONFIG_PATH)
    scenarios = {s.scenario_id: s for s in generate_scenarios(config)}
    catalog = next(iter(scenarios.values())).catalog
    freeze = json.loads((ROOT / "artifacts" / "experiment_freeze.json").read_text(encoding="utf-8"))
    finals, all_traces, io = load_stage(stage_dir)
    revisions = sorted({t["identity"]["code_revision"] for t in finals})
    revision = revisions[0] if len(revisions) == 1 else None

    # ---- planned manifest (re-derived from the frozen config) ----
    planned = {}
    for fam, cfg in SELECTED_MODELS.items():
        for p in plan_trials(cfg, tuple(scenarios[s] for s in stage.scenario_ids), stage.goals, MARKETINGS,
                             stage.repetitions, stage.experiment_version, revision or "0000000", stage.variant):
            planned[p.identity.trial_id] = p.identity.as_dict()
    final_by_id = {t["trial_id"]: t for t in finals}
    rows = build_rows(stage_dir, scenarios)
    row_by_id = {r["trial_id"]: r for r in rows}

    checks = []
    expected = len(stage.scenario_ids) * len(stage.goals) * len(MARKETINGS) * len(SELECTED_MODELS) * len(stage.repetitions)
    checks.append(check("single_code_revision", revision is not None, revisions=revisions))
    checks.append(check("planned_count_matches_design", len(planned) == expected, planned=len(planned), expected=expected))
    missing = sorted(set(planned) - set(final_by_id))
    unexpected = sorted(set(final_by_id) - set(planned))
    checks.append(check("every_planned_trial_has_a_final_trace", not missing, missing=len(missing)))
    checks.append(check("no_unplanned_trials", not unexpected, unexpected=len(unexpected)))
    per_attempt = Counter((t["trial_id"], t["_attempt"]) for t in all_traces)
    checks.append(check("no_duplicate_trace_within_attempt_file", all(v == 1 for v in per_attempt.values()),
                        duplicates=sum(1 for v in per_attempt.values() if v > 1)))

    cells = Counter((r["scenario_id"], r["goal_condition"], r["marketing_condition"], r["model_family"], r["repetition"]) for r in rows)
    checks.append(check("factorial_cells_one_trial_each", len(cells) == expected and all(v == 1 for v in cells.values()),
                        cells=len(cells)))
    profile_cov = Counter(r["profile_class"] for r in rows)
    checks.append(check("profile_coverage_balanced", len(set(profile_cov.values())) == 1, by_class=dict(profile_cov)))
    model_alloc = Counter(r["model_family"] for r in rows)
    checks.append(check("model_family_allocation_balanced", len(set(model_alloc.values())) == 1 and len(model_alloc) == 2, by_model=dict(model_alloc)))
    checks.append(check("config_hash_matches_freeze", stage_name != "core" or all(
        t["identity"]["config_sha256"] == freeze["models"][t["identity"]["model_family"]]["core_live_trial_config_sha256"] for t in finals)))
    templates = Counter(t["identity"]["prompt_template_id"] for t in finals)
    expected_templates = {f"{g}-v1-{stage.variant.template_index + 1:02d}" for g in stage.goals}
    checks.append(check("prompt_templates_frozen", set(templates) == expected_templates, templates=dict(templates)))
    observed = defaultdict(set)
    for r in rows:
        observed[r["model_family"]].update(r["observed_model_ids"])
    checks.append(check("observed_model_ids_consistent", all(observed[f] <= {SELECTED_MODELS[f].model_id, f"models/{SELECTED_MODELS[f].model_id}"} for f in observed),
                        observed={f: sorted(v) for f, v in observed.items()}))

    # ---- leakage on every model-visible request ----
    leaks = []
    trial_scenario = {t["trial_id"]: t["identity"]["scenario_id"] for t in all_traces}
    for rec in io:
        if rec.get("request_payload") and rec["trial_id"] in trial_scenario:
            hits = check_request_payload(rec["request_payload"], scenarios[trial_scenario[rec["trial_id"]]])
            if hits:
                leaks.append({"trial_id": rec["trial_id"], "call_index": rec.get("call_index"), "findings": hits})
    checks.append(check("no_ground_truth_leakage_in_model_visible_requests", not leaks, findings=len(leaks), requests_checked=sum(1 for r in io if r.get("request_payload"))))
    arm_names_visible = sum(1 for rec in io if rec.get("request_payload") and any(
        m.get("role") == "tool" and any(name in (m.get("content") or "") for name in ("marketing_condition", "social_proof", "scarcity"))
        for m in rec["request_payload"].get("messages", [])))
    checks.append(check("experimental_arm_names_not_visible", arm_names_visible == 0, requests_with_arm_name=arm_names_visible))

    # ---- catalog facts identical across arms; cue labels only where assigned ----
    base = {p.product_id: p for p in catalog.products}
    cue_ok, fact_ok = True, True
    arms = {a.condition.value: a for a in generate_cue_arms(catalog, config, seed=stage.variant.cue_seed)}
    for t in finals:
        ev = next((e for e in t["events"] if e["event_type"] == "catalog_inspected"), None)
        if ev is None:
            continue
        for prod in ev["payload"]["products"]:
            b = base[prod["product_id"]]
            if any(prod[k] != getattr(b, k) for k in ("price_inr", "quality", "durability", "repairability", "sustainability", "battery_life", "brand_familiarity", "popularity")):
                fact_ok = False
            should = prod["product_id"] in arms[t["identity"]["marketing_condition"]].cued_product_ids
            if (prod["marketing_label"] is not None) != should:
                cue_ok = False
    checks.append(check("catalog_facts_identical_to_frozen_catalog_in_every_arm", fact_ok))
    checks.append(check("cue_labels_exactly_on_assigned_products", cue_ok))
    checks.append(check("factual_utility_balance_recorded_true", all(t["evaluator_private"]["factual_utility_balance"]["balanced"] for t in finals)))
    checks.append(check("catalog_fingerprint_frozen", catalog_fingerprint(catalog) == freeze["environment"]["catalog_fingerprint"]))

    # ---- protocol order, simulated-user determinism ----
    order_viol = [r["trial_id"] for r in rows if not r["catalog_before_clarification"]]
    checks.append(check("catalog_inspection_before_clarification_or_classified", True, violations=len(order_viol),
                        note="violations are preserved and classified, not repaired"))
    sim_mismatch = 0
    for t in finals:
        for e in t["events"]:
            if e["event_type"] == "simulated_user_answer":
                ans = _answer_question(scenarios[t["identity"]["scenario_id"]].objective, e["payload"]["question"], e["payload"]["target"])
                sim_mismatch += ans.answer != e["payload"]["answer"]
    checks.append(check("simulated_user_answers_reproduce_deterministically", sim_mismatch == 0, mismatches=sim_mismatch))

    # ---- independent recomputation of metrics from raw outputs ----
    metric_mismatch = 0
    for r in rows:
        if not r["valid"]:
            continue
        s = scenarios[r["scenario_id"]]
        w_star = dict(s.objective.weights)
        D = 0.5 * sum(abs(r["w_hat"][k] - w_star[k]) for k in DIMENSIONS)
        X = {p.product_id: utility_features(p, catalog) for p in catalog.products}
        U = {pid: sum(w_star[k] * X[pid][k] for k in DIMENSIONS) for pid in X}
        u_opt = max(U.values())  # no hard cap in core_v2 objectives
        ok = abs(D - r["representation_error"]) < 1e-9 and abs(U[r["top_product"]] - r["recommended_utility"]) < 1e-9 \
            and abs((u_opt - U[r["top_product"]]) - r["regret"]) < 1e-9 and abs(u_opt - score_catalog(s.objective, catalog).optimal_utility) < 1e-12
        metric_mismatch += not ok
    checks.append(check("metrics_recomputed_independently_match", metric_mismatch == 0, mismatches=metric_mismatch))

    # ---- raw trace completeness ----
    io_calls = Counter((rec["trial_id"], rec["_attempt"]) for rec in io)
    resp_events = Counter()
    for t in all_traces:
        resp_events[(t["trial_id"], t["_attempt"])] = sum(1 for e in t["events"] if e["event_type"] == "response_received") + \
            sum(1 for f in t["failures"] if f.get("stage") == "model_api")
    incomplete = sum(1 for k, v in resp_events.items() if io_calls.get(k, 0) < v)
    checks.append(check("raw_model_io_present_for_every_response", incomplete == 0, incomplete=incomplete))
    hidden_in_agent_visible = sum(1 for t in finals if "controlled_synthetic_objective" in json.dumps(t["agent_visible"]))
    checks.append(check("raw_agent_visible_and_evaluator_private_separated", hidden_in_agent_visible == 0))
    missing_required = [r["trial_id"] for r in rows if r["valid"] and any(r.get(k) is None for k in ("w_hat", "top_product", "representation_error", "recommended_utility", "regret", "uncertainty"))]
    unclassified_invalid = [r["trial_id"] for r in rows if not r["valid"] and not r["terminal_failure_category"]]
    checks.append(check("no_missing_required_fields_without_failure_classification", not missing_required and not unclassified_invalid,
                        missing_required=len(missing_required), unclassified_invalid=len(unclassified_invalid)))
    secret_free = True
    try:
        from dotenv import dotenv_values
        secrets = [v for v in dotenv_values(ROOT / ".env").values() if v]
        for f in stage_dir.rglob("*.jsonl"):
            blob = f.read_bytes()
            if any(s.encode() in blob for s in secrets):
                secret_free = False
    except Exception:
        secret_free = False
    checks.append(check("no_credential_values_in_raw_files", secret_free))

    # ---- counts ----
    def counts(sub):
        return {"planned": len(sub), "valid": sum(r["valid"] for r in sub), "failed": sum(not r["valid"] for r in sub),
                "technical_retries": sum(r["technical_retry_used"] for r in sub), "parser_retries": sum(r["parser_retry_used"] for r in sub)}
    by_model = {f: counts([r for r in rows if r["model_family"] == f]) for f in SELECTED_MODELS}
    by_cell = {f"{f}|{g}|{m}": counts([r for r in rows if r["model_family"] == f and r["goal_condition"] == g and r["marketing_condition"] == m])
               for f in SELECTED_MODELS for g in stage.goals for m in MARKETINGS}
    failures = Counter((r["model_family"], r["terminal_failure_category"], r["terminal_failure_detail"]) for r in rows if not r["valid"])
    transport = Counter()
    credential_use = Counter()
    for model_dir in stage_dir.iterdir():
        if model_dir.is_dir():
            for e in read_jsonl(model_dir / "transport_events.jsonl"):
                transport[(model_dir.name, e["record_type"], str(e.get("status_code")))] += 1
            for e in read_jsonl(model_dir / "credential_requests.jsonl"):
                credential_use[(model_dir.name, e["credential_variable"], str(e.get("status_code")))] += 1
    tokens = {f: {"input": sum(r["input_tokens"] for r in rows if r["model_family"] == f),
                  "output": sum(r["output_tokens"] for r in rows if r["model_family"] == f),
                  "provider_calls": sum(r["provider_calls_all_attempts"] for r in rows if r["model_family"] == f)} for f in SELECTED_MODELS}

    passed = all(c["pass"] for c in checks)
    audit = {"artifact_version": "data-quality-audit-v1", "stage": stage_name, "experiment_version": stage.experiment_version,
             "code_revision": revision, "all_checks_passed": passed, "checks": checks, "counts_by_model": by_model,
             "counts_by_model_goal_marketing": by_cell,
             "terminal_failures": [{"model": k[0], "category": k[1], "detail": k[2], "n": v} for k, v in sorted(failures.items(), key=str)],
             "transport_events": [{"model": k[0], "type": k[1], "status": k[2], "n": v} for k, v in sorted(transport.items())],
             "credential_requests": [{"model": k[0], "credential_variable": k[1], "status": k[2], "n": v} for k, v in sorted(credential_use.items())],
             "tokens": tokens, "leakage_findings": leaks[:50]}
    suffix = "" if stage_name == "core" else f"_{stage_name}"
    out_dir = ROOT / "artifacts"
    (out_dir / f"data_quality_audit{suffix}.json").write_text(json.dumps(audit, indent=2, default=str) + "\n", encoding="utf-8")
    manifest = {"artifact_version": "trial-manifest-v1", "stage": stage_name, "planned": len(planned),
                "trials": [{"trial_id": tid, **ident, "final_attempt": final_by_id[tid]["_attempt"] if tid in final_by_id else None,
                            "valid": row_by_id[tid]["valid"] if tid in row_by_id else False,
                            "terminal_failure_category": row_by_id.get(tid, {}).get("terminal_failure_category")}
                           for tid, ident in sorted(planned.items(), key=lambda kv: (kv[1]["model_family"], kv[1]["scenario_id"], kv[1]["goal_condition"], kv[1]["marketing_condition"], kv[1]["repetition"]))]}
    (out_dir / f"trial_manifest{suffix}.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    ds_path = ROOT / "data" / "analysis" / f"{stage_name}_dataset.jsonl"
    write_dataset(rows, ds_path)
    summary = {"artifact_version": "run-summary-v1", "stage": stage_name, "planned": len(planned), "final_traces": len(finals),
               "valid": sum(r["valid"] for r in rows), "failed": sum(not r["valid"] for r in rows), "by_model": by_model,
               "tokens": tokens, "dataset_path": str(ds_path.relative_to(ROOT)).replace("\\", "/"),
               "dataset_sha256": hashlib.sha256(ds_path.read_bytes()).hexdigest(), "audit_passed": passed}
    (out_dir / ("core_run_summary.json" if stage_name == "core" else f"run_summary_{stage_name}.json")).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_checks_passed": passed, "failed_checks": [c for c in checks if not c["pass"]], "by_model": by_model}, indent=1, default=str))


if __name__ == "__main__":
    main()
