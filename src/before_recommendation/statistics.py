"""Pre-specified matched contrasts, scenario-cluster bootstrap and factorial models.

Implements analysis/analysis_plan.md v1.0.0:
* repetitions are averaged within scenario x goal x marketing x model cells;
* commercial = equal-weight mean of scarcity, social proof and discount cells;
* model-specific scenario contrasts are averaged with equal model weights;
* 10,000 scenario-level paired bootstrap resamples, seed 20260930, percentile CI;
* factorial models with scenario-clustered robust SEs, model family fixed;
* Holm adjustment across the four primary contrasts.

A scenario contributes to a contrast only when every cell the contrast needs has
at least one valid run (complete-case at scenario level); counts are reported.
"""

from __future__ import annotations

from collections import defaultdict
import math
import warnings

import numpy as np
import pandas as pd


BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260930
CUES = ("scarcity", "social_proof", "discount")
PRIMARY_OUTCOMES = {
    "clarification": "Clarification rate (risk difference)",
    "representation_error": "Preference-representation error (Delta D)",
    "recommended_utility": "Recommendation utility",
    "regret": "Regret",
}


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["clarification"] = df["clarification"].astype(float)
    return df


def cell_means(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    valid = df[df["valid"]]
    return (valid.groupby(["scenario_id", "model_family", "goal_condition", "marketing_condition"])[outcome]
            .mean().rename("y").reset_index())


def _scenario_contrasts(cells: pd.DataFrame, contrast: str, cue: str | None, models: list[str]) -> pd.DataFrame:
    """Return per-scenario, per-model contrast values (NaN if a needed cell is missing)."""
    wide = cells.pivot_table(index=["scenario_id", "model_family"], columns=["goal_condition", "marketing_condition"], values="y")
    arms = CUES if cue is None else (cue,)

    def diff(goal: str) -> pd.Series:
        needed = [(goal, "neutral")] + [(goal, a) for a in arms]
        if any(col not in wide.columns for col in needed):
            return pd.Series(np.nan, index=wide.index)
        commercial = wide[[(goal, a) for a in arms]].mean(axis=1, skipna=False)
        return commercial - wide[(goal, "neutral")]

    if contrast == "commercial_vs_neutral_ambiguous":
        values = diff("ambiguous")
    elif contrast == "commercial_vs_neutral_explicit":
        values = diff("explicit")
    elif contrast == "moderation_ambiguous_minus_explicit":
        values = diff("ambiguous") - diff("explicit")
    elif contrast == "ambiguous_minus_explicit":
        cols_a = [("ambiguous", m) for m in ("neutral",) + CUES]
        cols_e = [("explicit", m) for m in ("neutral",) + CUES]
        if any(c not in wide.columns for c in cols_a + cols_e):
            values = pd.Series(np.nan, index=wide.index)
        else:
            values = wide[cols_a].mean(axis=1, skipna=False) - wide[cols_e].mean(axis=1, skipna=False)
    else:
        raise ValueError(contrast)
    out = values.rename("d").reset_index()
    return out[out["model_family"].isin(models)]


def matched_contrast(df: pd.DataFrame, outcome: str, contrast: str, *, cue: str | None = None,
                     model: str | None = None, replicates: int = BOOTSTRAP_REPLICATES,
                     seed: int = BOOTSTRAP_SEED) -> dict[str, object]:
    models = sorted(df["model_family"].unique()) if model is None else [model]
    per = _scenario_contrasts(cell_means(df, outcome), contrast, cue, models)
    wide = per.pivot(index="scenario_id", columns="model_family", values="d")
    for m in models:
        if m not in wide.columns:
            wide[m] = np.nan
    wide = wide[models]
    complete = wide.dropna()
    n_s = len(complete)
    if n_s == 0:
        return {"outcome": outcome, "contrast": contrast, "cue": cue or "commercial", "model": model or "pooled_equal_weight",
                "estimate": None, "ci_low": None, "ci_high": None, "n_scenarios": 0,
                "n_scenarios_excluded_incomplete": int(len(wide))}
    scenario_values = complete.mean(axis=1).to_numpy()  # equal model weights
    estimate = float(scenario_values.mean())
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_s, size=(replicates, n_s))
    boot = scenario_values[draws].mean(axis=1)
    low, high = np.percentile(boot, [2.5, 97.5])
    # Two-sided bootstrap p-value (null-centred percentile method), reported alongside CIs.
    centred = boot - boot.mean()
    p_boot = float(min(1.0, np.mean(np.abs(centred) >= abs(estimate)) + 1.0 / replicates))
    return {
        "outcome": outcome, "contrast": contrast, "cue": cue or "commercial",
        "model": model or "pooled_equal_weight",
        "estimate": estimate, "ci_low": float(low), "ci_high": float(high),
        "bootstrap_p_two_sided": p_boot,
        "n_scenarios": int(n_s), "n_scenarios_excluded_incomplete": int(len(wide) - n_s),
        "bootstrap_replicates": replicates, "bootstrap_seed": seed,
        "model_specific_means": {m: float(complete[m].mean()) for m in models},
    }


def holm(pvalues: list[float | None]) -> list[float | None]:
    indexed = [(p, i) for i, p in enumerate(pvalues) if p is not None]
    indexed.sort()
    m = len(indexed)
    adjusted: list[float | None] = [None] * len(pvalues)
    running = 0.0
    for rank, (p, i) in enumerate(indexed):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[i] = running
    return adjusted


def factorial_model(df: pd.DataFrame, outcome: str) -> dict[str, object]:
    """outcome ~ goal * marketing + model_family with scenario-clustered SEs."""
    import statsmodels.formula.api as smf

    valid = df[df["valid"]].copy()
    valid["goal"] = pd.Categorical(valid["goal_condition"], ["explicit", "ambiguous"])
    valid["marketing"] = pd.Categorical(valid["marketing_condition"], ["neutral", *CUES])
    valid["y"] = valid[outcome].astype(float)
    formula = "y ~ C(goal) * C(marketing) + C(model_family)"
    groups = pd.factorize(valid["scenario_id"])[0]
    result: dict[str, object] = {"outcome": outcome, "formula": formula.replace("y", outcome, 1),
                                 "n_runs": int(len(valid)), "n_clusters": int(len(set(groups))),
                                 "covariance": "cluster-robust by scenario_id"}
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if outcome == "clarification":
                if valid["y"].nunique() < 2:
                    raise ValueError("outcome has no variation")
                fit = smf.logit(formula, valid).fit(disp=False, maxiter=200, cov_type="cluster", cov_kwds={"groups": groups})
                result["family"] = "logit"
                converged = bool(fit.mle_retvals.get("converged", False))
            else:
                fit = smf.ols(formula, valid).fit(cov_type="cluster", cov_kwds={"groups": groups})
                result["family"] = "ols"
                converged = True
        result["converged"] = converged
        result["warnings"] = sorted({str(w.message)[:160] for w in caught})
        ci = fit.conf_int()
        result["coefficients"] = [
            {"term": term, "estimate": float(fit.params[term]), "se": float(fit.bse[term]),
             "ci_low": float(ci.loc[term, 0]), "ci_high": float(ci.loc[term, 1]), "p": float(fit.pvalues[term])}
            for term in fit.params.index
        ]
        if not all(math.isfinite(c["se"]) for c in result["coefficients"]):
            result["assumption_note"] = "non-finite standard errors (likely quasi-separation); matched bootstrap remains primary"
    except Exception as exc:  # documented failure, not a silent switch
        result["fit_failed"] = True
        result["failure_reason"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    return result


def repeat_stability(df: pd.DataFrame) -> dict[str, object]:
    groups = defaultdict(list)
    for _, r in df[df["valid"]].iterrows():
        groups[(r["scenario_id"], r["goal_condition"], r["marketing_condition"], r["model_family"])].append(r)
    out: dict[str, dict] = {}
    for model in sorted(df["model_family"].unique()):
        cells = [v for k, v in groups.items() if k[3] == model and len(v) >= 2]
        def agree(field: str) -> float | None:
            vals = [len({str(x[field]) for x in c}) == 1 for c in cells]
            return float(np.mean(vals)) if vals else None
        spreads = [c[0]["cell_weight_spread"] for c in cells if c[0]["cell_weight_spread"] is not None]
        out[model] = {
            "cells_with_2plus_valid_reps": len(cells),
            "clarification_decision_agreement": agree("clarification"),
            "question_target_agreement_among_all_rep_cells": agree("question_target_normalized"),
            "top_product_agreement": agree("top_product"),
            "weight_spread_mean_max_pairwise_half_l1": float(np.mean(spreads)) if spreads else None,
            "weight_spread_median": float(np.median(spreads)) if spreads else None,
        }
    return out
