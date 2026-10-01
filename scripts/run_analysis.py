"""Pre-specified analysis (analysis/analysis_plan.md v1.0.0) of a frozen dataset.

Usage: python scripts/run_analysis.py [stage]   (default core; reads data/analysis/<stage>_dataset.jsonl)
Writes artifacts/analysis/<stage>_results.json. Refuses to run inference on the
core if the data-quality audit did not pass.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.statistics import (  # noqa: E402
    CUES, PRIMARY_OUTCOMES, factorial_model, holm, matched_contrast, repeat_stability, to_frame,
)

TAXONOMY = ("silent_defaulting", "cue_driven_attribute_substitution", "leading_clarification", "under_questioning",
            "over_questioning", "unsupported_marketing_evidence", "preference_weight_instability", "ranking_inconsistency",
            "uncertainty_failure", "catalog_inspection_order_violation", "invalid_structured_output", "tool_or_serving_failure")


def load(stage: str) -> pd.DataFrame:
    rows = [json.loads(line) for line in (ROOT / "data" / "analysis" / f"{stage}_dataset.jsonl").read_text(encoding="utf-8").splitlines()]
    df = to_frame(rows)
    df["price_question"] = (df["clarification"] > 0) & ((df["question_target_normalized"] == "price") | df["question_price_related"].astype(bool))
    for col in ("evidence_mentions_cue", "top_is_cued", "constraint_violated"):
        df[col] = df[col].astype("float") if col in df else np.nan
    return df


def contrasts_for(df: pd.DataFrame, outcome: str, contrast: str, models: list[str], cue: str | None = None) -> dict:
    pooled = matched_contrast(df, outcome, contrast, cue=cue)
    per_model = {m: matched_contrast(df, outcome, contrast, cue=cue, model=m) for m in models}
    return {"pooled": pooled, "by_model": per_model}


def describe(df: pd.DataFrame, models: list[str]) -> dict:
    valid = df[df["valid"]]
    out = {}
    for (m, g, k), sub in valid.groupby(["model_family", "goal_condition", "marketing_condition"]):
        out[f"{m}|{g}|{k}"] = {
            "valid_runs": int(len(sub)), "planned_runs": int(len(df[(df.model_family == m) & (df.goal_condition == g) & (df.marketing_condition == k)])),
            "clarification_rate": float(sub["clarification"].mean()), "representation_error_mean": float(sub["representation_error"].mean()),
            "representation_error_sd": float(sub["representation_error"].std(ddof=1)), "utility_mean": float(sub["recommended_utility"].mean()),
            "regret_mean": float(sub["regret"].mean()), "regret_zero_share": float((sub["regret"] < 1e-12).mean()),
            "uncertainty_mean": float(sub["uncertainty"].mean()), "evidence_mentions_cue_rate": float(sub["evidence_mentions_cue"].mean()),
            "top_is_cued_rate": float(sub["top_is_cued"].mean()), "cued_mean_rank": float(sub["cued_mean_rank"].mean()),
            "constraint_violation_rate": float(sub["constraint_violated"].mean()),
            "price_question_rate": float(sub["price_question"].mean()),
        }
    return out


def question_targets(df: pd.DataFrame) -> dict:
    out = defaultdict(dict)
    clar = df[df["valid"] & (df["clarification"] > 0)]
    for (m, g, k), sub in clar.groupby(["model_family", "goal_condition", "marketing_condition"]):
        norm = sub["question_target_normalized"].fillna("unsupported_or_compound")
        out[m][f"{g}|{k}"] = {"n_clarifications": int(len(sub)), "normalized_target_counts": dict(Counter(norm)),
                              "answer_supported_rate": float(sub["clarification_answer_supported"].astype(float).mean())}
    return out


def h4_separation(df: pd.DataFrame) -> dict:
    pairs = df[df["valid"] & df["commercial"] & df["delta_representation_error"].notna()]
    out = {}
    for label, sub in [("pooled", pairs)] + [(m, pairs[pairs.model_family == m]) for m in sorted(df.model_family.unique())]:
        for goal in ("ambiguous", "explicit"):
            g = sub[sub.goal_condition == goal]
            if g.empty:
                continue
            shifted = g["weight_shift_vs_neutral"] > 0.05
            out[f"{label}|{goal}"] = {
                "matched_pairs": int(len(g)), "top_product_changed_rate": float(g["top_changed_vs_neutral"].astype(float).mean()),
                "weight_shift_vs_neutral_mean": float(g["weight_shift_vs_neutral"].mean()),
                "share_weight_shift_gt_0_05": float(shifted.mean()),
                "share_weight_shift_gt_0_05_with_same_top_product": float((shifted & ~g["top_changed_vs_neutral"].astype(bool)).mean()),
                "mean_abs_delta_D": float(g["delta_representation_error"].abs().mean()),
            }
    return out


def taxonomy(df: pd.DataFrame) -> dict:
    out = {}
    for m in ["all"] + sorted(df.model_family.unique()):
        sub = df if m == "all" else df[df.model_family == m]
        out[m] = {}
        for cat in TAXONOMY:
            flags = sub["taxonomy"].map(lambda t: bool(t.get(cat)))
            by_arm = {f"{g}|{k}": int(flags[(sub.goal_condition == g) & (sub.marketing_condition == k)].sum())
                      for g in sorted(sub.goal_condition.unique()) for k in ("neutral", *CUES)}
            out[m][cat] = {"count": int(flags.sum()), "rate_over_planned": float(flags.mean()), "by_goal_marketing": by_arm}
    return out


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "core"
    if stage == "core":
        audit = json.loads((ROOT / "artifacts" / "data_quality_audit.json").read_text(encoding="utf-8"))
        if not audit["all_checks_passed"]:
            raise SystemExit("Data-quality audit failed; inference refused (analysis plan section 5).")
    df = load(stage)
    models = sorted(df["model_family"].unique())
    goals = sorted(df["goal_condition"].unique())
    results: dict[str, object] = {"artifact_version": "analysis-results-v1", "stage": stage, "analysis_plan": "analysis-plan-v1.0.0",
                                  "n_planned_runs": int(len(df)), "n_valid_runs": int(df["valid"].sum()),
                                  "n_scenarios": int(df["scenario_id"].nunique()), "models": models,
                                  "descriptives": describe(df, models), "question_targets": question_targets(df)}

    # Primary: commercial vs neutral under ambiguity, four outcomes, Holm across the four.
    primary = {o: contrasts_for(df, o, "commercial_vs_neutral_ambiguous", models) for o in PRIMARY_OUTCOMES}
    adj = holm([primary[o]["pooled"].get("bootstrap_p_two_sided") for o in PRIMARY_OUTCOMES])
    for o, a in zip(PRIMARY_OUTCOMES, adj):
        primary[o]["pooled"]["holm_adjusted_p"] = a
    results["primary_commercial_vs_neutral_ambiguous"] = primary

    if "explicit" in goals:
        results["secondary_commercial_vs_neutral_explicit"] = {o: contrasts_for(df, o, "commercial_vs_neutral_explicit", models) for o in PRIMARY_OUTCOMES}
        results["secondary_moderation_ambiguous_minus_explicit"] = {o: contrasts_for(df, o, "moderation_ambiguous_minus_explicit", models) for o in PRIMARY_OUTCOMES}
        results["h1_ambiguous_minus_explicit_all_arms"] = {o: contrasts_for(df, o, "ambiguous_minus_explicit", models) for o in PRIMARY_OUTCOMES}

    cue_specific = {}
    for o in PRIMARY_OUTCOMES:
        fam = {c: contrasts_for(df, o, "commercial_vs_neutral_ambiguous", models, cue=c) for c in CUES}
        adj = holm([fam[c]["pooled"].get("bootstrap_p_two_sided") for c in CUES])
        for c, a in zip(CUES, adj):
            fam[c]["pooled"]["holm_adjusted_p_within_outcome"] = a
        cue_specific[o] = fam
    results["secondary_cue_specific_ambiguous"] = cue_specific

    secondary_outcomes = ("cued_mean_rank", "top_is_cued", "evidence_mentions_cue", "uncertainty", "constraint_violated", "price_question")
    results["secondary_outcomes_commercial_vs_neutral"] = {
        g: {o: contrasts_for(df, o, f"commercial_vs_neutral_{g}", models) for o in secondary_outcomes} for g in goals}
    results["h5_exploratory_discount_vs_neutral_price_question"] = {
        g: contrasts_for(df, "price_question", f"commercial_vs_neutral_{g}", models, cue="discount") for g in goals}
    results["h4_representation_recommendation_separation"] = h4_separation(df)
    results["factorial_models"] = {o: factorial_model(df, o) for o in PRIMARY_OUTCOMES} if len(goals) > 1 else {}
    results["factorial_models_by_model"] = {m: {o: factorial_model(df[df.model_family == m].assign(model_family=m), o) for o in PRIMARY_OUTCOMES}
                                            for m in models} if len(goals) > 1 else {}
    results["repeat_stability"] = repeat_stability(df)
    results["failure_taxonomy"] = taxonomy(df)
    results["missingness"] = {m: {"planned": int((df.model_family == m).sum()), "valid": int(((df.model_family == m) & df.valid).sum()),
                                  "terminal_failures": dict(Counter(df[(df.model_family == m) & ~df.valid]["terminal_failure_category"]))} for m in models}
    out_dir = ROOT / "artifacts" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{stage}_results.json").write_text(json.dumps(results, indent=2, default=float) + "\n", encoding="utf-8")
    for o in PRIMARY_OUTCOMES:
        p = primary[o]["pooled"]
        print(f"{o}: est={p['estimate']} CI=[{p['ci_low']}, {p['ci_high']}] n_s={p['n_scenarios']} holm_p={p.get('holm_adjusted_p')}")


if __name__ == "__main__":
    main()
