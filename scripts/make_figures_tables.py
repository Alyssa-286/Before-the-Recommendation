"""Generate paper figures and tables from the frozen datasets and analysis results only.

Usage: python scripts/make_figures_tables.py [stage]  (default core)
Writes outputs/figures/*.png|svg and outputs/tables/*.md|csv.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from before_recommendation.config import load_phase1_config  # noqa: E402
from before_recommendation.experiment_config import CORE_CONFIG_PATH, SELECTED_MODELS  # noqa: E402
from before_recommendation.scenarios import generate_scenarios  # noqa: E402
from before_recommendation.conditions import generate_cue_arms, MarketingCondition  # noqa: E402
from before_recommendation.evaluator import score_catalog  # noqa: E402

ARMS = ("neutral", "scarcity", "social_proof", "discount")
ARM_LABEL = {"neutral": "Neutral", "scarcity": "Scarcity", "social_proof": "Social proof", "discount": "Discount"}
ARM_COLOR = {"neutral": "#2a78d6", "scarcity": "#eb6834", "social_proof": "#1baf7a", "discount": "#eda100"}
MODEL_LABEL = {"google_gemini": "Gemini 3.1 Flash-Lite", "mistral": "Ministral 14B"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
OUTCOME_LABEL = {"clarification": "Clarification rate", "representation_error": "Representation error D",
                 "recommended_utility": "Recommendation utility", "regret": "Regret"}
FIG = ROOT / "outputs" / "figures"
TAB = ROOT / "outputs" / "tables"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def write_table(name: str, header: list[str], rows: list[list[object]], caption: str) -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    with (TAB / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([header, *rows])
    lines = [f"**{caption}**", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    (TAB / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(x, d=3):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def ci(p: dict, d=3) -> str:
    if p.get("estimate") is None:
        return "—"
    return f"{p['estimate']:.{d}f} [{p['ci_low']:.{d}f}, {p['ci_high']:.{d}f}]"


def load_rows(stage: str) -> list[dict]:
    return [json.loads(l) for l in (ROOT / "data" / "analysis" / f"{stage}_dataset.jsonl").read_text(encoding="utf-8").splitlines()]


def cell_ci(rows, model, goal, arm, key, B=2000, seed=20260930):
    """Cell mean with a scenario-cluster bootstrap 95% interval (descriptive)."""
    by_s = {}
    for r in rows:
        if r["valid"] and r["model_family"] == model and r["goal_condition"] == goal and r["marketing_condition"] == arm:
            by_s.setdefault(r["scenario_id"], []).append(float(r[key]))
    if not by_s:
        return np.nan, np.nan, np.nan
    vals = np.array([np.mean(v) for v in by_s.values()])
    rng = np.random.default_rng(seed)
    boot = vals[rng.integers(0, len(vals), (B, len(vals)))].mean(1)
    return vals.mean(), *np.percentile(boot, [2.5, 97.5])


def box(ax, x, y, w, h, text, fc="#ffffff", ec=INK2, fs=7, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fc, ec=ec, lw=1))
    t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK, weight=weight)
    renderer = ax.figure.canvas.get_renderer()
    (bx0, by0), (bx1, by1) = ax.transData.transform([(x, y), (x + w, y + h)])
    while fs > 4.5:
        ext = t.get_window_extent(renderer)
        if ext.width <= 0.92 * (bx1 - bx0) and ext.height <= 0.9 * (by1 - by0):
            break
        fs -= 0.25
        t.set_fontsize(fs)


def arrow(ax, x1, y1, x2, y2):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1))


def fig1_framework():
    fig, ax = plt.subplots(figsize=(7.2, 2.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 3.2); ax.axis("off")
    plt.rcParams["font.size"] = 7
    box(ax, 0.1, 1.9, 1.9, 0.9, "Goal ambiguity\n(ambiguous vs explicit)", fc="#eef4fc")
    box(ax, 0.1, 0.4, 1.9, 0.9, "Storefront cue\n(neutral, scarcity,\nsocial proof, discount)", fc="#fdf0ea")
    box(ax, 2.6, 1.15, 1.7, 0.9, "Catalog inspection &\nclarification decision\n(H5: question target)")
    box(ax, 4.9, 1.15, 1.7, 0.9, "Operational preference\nrepresentation  ŵ\n(H1–H3: error D, ΔD)", fc="#eaf7f1")
    box(ax, 7.2, 1.15, 1.2, 0.9, "Ranking &\nrecommendation")
    box(ax, 8.7, 1.15, 1.25, 0.9, "Utility, regret\n(H4: separation)", fc="#fdf6e6")
    arrow(ax, 2.0, 2.35, 2.6, 1.75); arrow(ax, 2.0, 0.85, 2.6, 1.45)
    arrow(ax, 4.3, 1.6, 4.9, 1.6); arrow(ax, 6.6, 1.6, 7.2, 1.6); arrow(ax, 8.4, 1.6, 8.7, 1.6)
    ax.text(5.0, 0.1, "Controlled latent objective w* (hidden from the agent) drives the simulated user and the evaluator only",
            ha="center", fontsize=7.5, color=INK2, style="italic")
    save(fig, "fig1_conceptual_framework")


def fig2_pipeline():
    fig, ax = plt.subplots(figsize=(7.2, 3.2)); ax.set_xlim(0, 10); ax.set_ylim(0, 4.2); ax.axis("off")
    steps = ["User request\n(frozen template)", "inspect_catalog\n(tool result: table\nwith cue labels)", "ask_clarification\n(≤ 1, optional)",
             "Simulated user\n(deterministic\nanswer from w*)", "submit_recommendation\n(weights, ranking,\nevidence, uncertainty)"]
    for i, s in enumerate(steps):
        box(ax, 0.1 + i * 2.0, 2.6, 1.8, 1.2, s, fc="#ffffff" if i != 3 else "#f4f3ef", fs=6.8)
        if i:
            arrow(ax, i * 2.0 - 0.1, 3.2, i * 2.0 + 0.1, 3.2)
    box(ax, 0.1, 0.4, 3.1, 1.3, "Agent-visible boundary\nsystem + user + tool results only;\nno w*, optimum, utility or arm name\n(automated leakage scan of every request)", fc="#eef4fc", fs=6.2)
    box(ax, 3.45, 0.4, 3.1, 1.3, "Independent deterministic evaluator\nD = ½Σ|ŵ−w*|,  U(p)=Σw*x,\nregret = U(p*) − U(top)", fc="#eaf7f1", fs=6.2)
    box(ax, 6.8, 0.4, 3.1, 1.3, "Logging & control\nraw I/O per call, append-only traces,\nSQLite checkpoint, 1 parser retry,\n1 technical re-run, credential pools", fc="#fdf6e6", fs=6.2)
    arrow(ax, 9.0, 2.6, 5.0, 1.7)
    save(fig, "fig2_experimental_pipeline")


def dot_panels(rows, key, ylabel, name, ylim=None):
    models = list(SELECTED_MODELS)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    for ax, model in zip(axes, models):
        for gi, goal in enumerate(("ambiguous", "explicit")):
            for ai, arm in enumerate(ARMS):
                m, lo, hi = cell_ci(rows, model, goal, arm, key)
                x = gi * 5 + ai
                ax.plot([x, x], [lo, hi], color=ARM_COLOR[arm], lw=2, solid_capstyle="round")
                ax.plot(x, m, "o", ms=8, color=ARM_COLOR[arm], mec=SURFACE, mew=2)
        ax.set_xticks([gi * 5 + ai for gi in range(2) for ai in range(4)])
        ax.set_xticklabels([ARM_LABEL[a] for a in ARMS] * 2, rotation=40, ha="right", fontsize=7.5)
        ax.text(1.5, 1.02, "Ambiguous goal", transform=ax.get_xaxis_transform(), ha="center", fontsize=8, color=INK2)
        ax.text(6.5, 1.02, "Explicit goal", transform=ax.get_xaxis_transform(), ha="center", fontsize=8, color=INK2)
        ax.set_title(MODEL_LABEL[model], fontsize=9, color=INK, pad=14)
        ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
        if ylim:
            ax.set_ylim(*ylim)
    axes[0].set_ylabel(ylabel)
    fig.text(0.5, -0.12, "Points: cell means over scenarios (repetitions averaged); bars: 95% scenario-bootstrap intervals.", ha="center", fontsize=7, color=INK2)
    save(fig, name)


def fig5_utility_regret(rows):
    models = list(SELECTED_MODELS)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    for ax, key, lab in zip(axes, ("recommended_utility", "regret"), ("Recommendation utility", "Regret")):
        for mi, model in enumerate(models):
            for gi, goal in enumerate(("ambiguous", "explicit")):
                for ai, arm in enumerate(ARMS):
                    m, lo, hi = cell_ci(rows, model, goal, arm, key)
                    x = mi * 10 + gi * 5 + ai
                    ax.plot([x, x], [lo, hi], color=ARM_COLOR[arm], lw=2)
                    ax.plot(x, m, "o", ms=7, color=ARM_COLOR[arm], mec=SURFACE, mew=2)
        ax.set_xticks([1.5, 6.5, 11.5, 16.5]); ax.set_xticklabels(["Gemini\nambig.", "Gemini\nexplicit", "Ministral\nambig.", "Ministral\nexplicit"], fontsize=7.5)
        ax.set_ylabel(lab); ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    handles = [plt.Line2D([], [], marker="o", ls="", color=ARM_COLOR[a], ms=7, label=ARM_LABEL[a]) for a in ARMS]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.06), fontsize=8)
    save(fig, "fig5_utility_regret")


def fig6_forest(results, robust):
    labels, ests, los, his = [], [], [], []
    for o in ("clarification", "representation_error", "recommended_utility", "regret"):
        block = results["primary_commercial_vs_neutral_ambiguous"][o]
        for src, p in [("Pooled", block["pooled"])] + [(MODEL_LABEL[m], block["by_model"][m]) for m in SELECTED_MODELS]:
            labels.append(f"{OUTCOME_LABEL[o]} — {src}"); ests.append(p["estimate"]); los.append(p["ci_low"]); his.append(p["ci_high"])
        for name, res in robust.items():
            p = res["primary_commercial_vs_neutral_ambiguous"][o]["pooled"]
            labels.append(f"{OUTCOME_LABEL[o]} — {name}"); ests.append(p["estimate"]); los.append(p["ci_low"]); his.append(p["ci_high"])
    n = len(labels)
    fig, ax = plt.subplots(figsize=(7.2, 0.24 * n + 0.8))
    y = np.arange(n)[::-1]
    for yi, e, lo, hi, lab in zip(y, ests, los, his, labels):
        if e is None:
            continue
        col = "#2a78d6" if "Pooled" in lab else "#52514e" if "robust" in lab.lower() else "#eb6834"
        ax.plot([lo, hi], [yi, yi], color=col, lw=2); ax.plot(e, yi, "o", color=col, ms=6, mec=SURFACE, mew=1.5)
    ax.axvline(0, color=INK2, lw=0.8, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=6.8)
    ax.set_xlabel("Commercial − neutral (ambiguous goal), matched estimate with 95% scenario-bootstrap CI")
    ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
    save(fig, "fig6_cross_model_robustness")


def fig7_failure_pathway(rows):
    """Representative example chosen by a pre-specified rule: most frequent research-failure
    category among valid ambiguous commercial runs; first trial by sorted trial_id."""
    cats = ("cue_driven_attribute_substitution", "unsupported_marketing_evidence", "leading_clarification", "silent_defaulting", "under_questioning")
    counts = {c: sum(1 for r in rows if r["valid"] and r["commercial"] and r["goal_condition"] == "ambiguous" and r["taxonomy"].get(c)) for c in cats}
    cat = max(cats, key=lambda c: (counts[c], -cats.index(c)))
    pick = sorted((r for r in rows if r["valid"] and r["commercial"] and r["goal_condition"] == "ambiguous" and r["taxonomy"].get(cat)), key=lambda r: r["trial_id"])
    if not pick:
        return None
    r = pick[0]
    fig, ax = plt.subplots(figsize=(7.2, 2.7)); ax.set_xlim(0, 10); ax.set_ylim(0, 3.4); ax.axis("off")
    q = (r["clarification_question"] or "(no clarification asked)")[:110]
    steps = [f"Arm: {ARM_LABEL[r['marketing_condition']]}\nModel: {MODEL_LABEL[r['model_family']]}\nScenario {r['scenario_id'][-3:]} ({r['profile_class'].replace('_', ' ')})",
             f"Clarification: {'yes' if r['clarification'] else 'no'}\nTarget: {r['question_target_raw'] or '—'}",
             "ŵ = " + ", ".join(f"{k[:4]} {v:.2f}" for k, v in r["w_hat"].items()) + "\nw* = " + ", ".join(f"{k[:4]} {v:.2f}" for k, v in r["w_star"].items()),
             f"Top: {r['top_product']} ({'cued' if r['top_is_cued'] else 'not cued'})\nD = {r['representation_error']:.3f}; regret = {r['regret']:.3f}"]
    for i, s in enumerate(steps):
        box(ax, 0.05 + i * 2.5, 1.6, 2.35, 1.5, s, fs=6.8, fc="#ffffff" if i != 3 else "#fdf6e6")
        if i:
            arrow(ax, i * 2.5 - 0.1, 2.35, i * 2.5 + 0.05, 2.35)
    ax.text(0.05, 1.15, f"Category (pre-specified rule): {cat.replace('_', ' ')} — {counts[cat]} of the eligible runs", fontsize=7.5, color=INK)
    ax.text(0.05, 0.75, f"Question text: {q}", fontsize=6.8, color=INK2)
    ax.text(0.05, 0.35, f"Trial ID: {r['trial_id'][:16]}…  (full trace in data/core/)", fontsize=6.8, color=INK2)
    save(fig, "fig7_failure_pathway")
    return {"category": cat, "category_counts": counts, "trial_id": r["trial_id"]}


def fig8_d_vs_utility(rows):
    pairs = [r for r in rows if r["valid"] and r["commercial"] and r.get("delta_representation_error") is not None]
    if not pairs:
        return
    neutral = {r["trial_id"]: r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for ax, model in zip(axes, SELECTED_MODELS):
        for arm in ARMS[1:]:
            sub = [r for r in pairs if r["model_family"] == model and r["marketing_condition"] == arm and r["goal_condition"] == "ambiguous"]
            xs = [r["delta_representation_error"] for r in sub]
            ys = [r["recommended_utility"] - neutral[r["matched_neutral_trial_id"]]["recommended_utility"] for r in sub]
            ax.scatter(xs, ys, s=14, color=ARM_COLOR[arm], alpha=0.75, edgecolors=SURFACE, linewidths=0.6, label=ARM_LABEL[arm])
        ax.axhline(0, color=INK2, lw=0.7); ax.axvline(0, color=INK2, lw=0.7)
        ax.set_title(MODEL_LABEL[model], fontsize=9); ax.set_xlabel("ΔD vs matched neutral run")
        ax.grid(color=GRID, lw=0.5); ax.set_axisbelow(True)
    axes[0].set_ylabel("Δ utility vs matched neutral run"); axes[0].legend(frameon=False, fontsize=7)
    fig.text(0.5, -0.06, "Ambiguous goal; each point is one commercial run matched to the neutral run of the same scenario and repetition.", ha="center", fontsize=7, color=INK2)
    save(fig, "fig8_representation_vs_utility")


def tables(results, robust, rows):
    cfg = load_phase1_config(CORE_CONFIG_PATH)
    sc = generate_scenarios(cfg)
    cat = sc[0].catalog
    arms = generate_cue_arms(cat, cfg)
    write_table("table1_experimental_conditions", ["Factor", "Levels", "Implementation"], [
        ["Goal condition", "Ambiguous; Explicit", "Frozen templates ambiguous-v1-01 / explicit-v1-01 rendered from the same latent objective"],
        ["Marketing condition", "Neutral; Scarcity; Social proof; Discount", "Labels 'Only 2 units remaining.', '50,000+ students chose this.', '20% promotional discount.' on 5 fixed products; facts unchanged"],
        ["Model family", "Google Gemini; Mistral", "gemini-3.1-flash-lite; ministral-14b-2512 (free routes, provider-default temperature)"],
        ["Repetition", "1–3", "Independent calls of the same cell"],
        ["Scenario/profile", "40", "5 profile classes × 8 jittered objectives"],
        ["Core runs", "1,920", "40 × 2 × 4 × 2 × 3"]], "Table 1. Experimental conditions")
    cls = {}
    for s in sc:
        cls.setdefault(s.objective.profile_class, []).append(s)
    rows2 = []
    for c, ss in sorted(cls.items()):
        W = np.array([[s.objective.weight(k) for k in ("price", "quality", "durability", "sustainability")] for s in ss])
        opt = sorted({score_catalog(s.objective, cat).optimal_product_id for s in ss})
        rows2.append([c.replace("_", " "), len(ss), *[f"{W[:, i].mean():.2f} ({W[:, i].min():.2f}–{W[:, i].max():.2f})" for i in range(4)], ", ".join(o.replace("LumaBook_", "") for o in opt)])
    cued = next(a for a in arms if a.condition is MarketingCondition.SCARCITY).cued_product_ids
    rows2.append(["Catalog", "20 products", "price INR 35k–95k", "scores 40–100", f"cued: {', '.join(c.replace('LumaBook_', '') for c in cued)}", f"seed {cfg.catalog_seed}", "acceptance v1.0.0 passed"])
    write_table("table2_scenario_construction", ["Profile class", "n", "w price mean (range)", "w quality", "w durability", "w sustainability", "Optimal products"], rows2,
                "Table 2. Scenario and profile construction (controlled synthetic objectives)")
    write_table("table_metric_definitions", ["Metric", "Definition", "Level"], [
        ["Clarification rate", "Share of valid runs with one ask_clarification call after inspection", "run"],
        ["Representation error D", "½ Σ_k |ŵ_k − w*_k| over price, quality, durability, sustainability", "run"],
        ["ΔD", "Matched commercial − neutral difference in D (same scenario, model, repetition)", "contrast"],
        ["Utility U", "Σ_k w*_k x_pk of the top-ranked product (normalized factual scores)", "run"],
        ["Regret", "U(optimal feasible product) − U(top-ranked product)", "run"],
        ["Cued mean rank", "Mean rank of the 5 cued products in the agent's ranking (unranked = 21)", "run"],
        ["Evidence mentions cue", "evidence_used or explanation contains a pre-registered cue term", "run"],
        ["Price question", "Clarification targeted price (normalized target or price terms)", "run"]], "Metric definitions")
    prim = results["primary_commercial_vs_neutral_ambiguous"]
    t3 = []
    for o in prim:
        p = prim[o]["pooled"]
        t3.append([OUTCOME_LABEL[o], ci(p), p["n_scenarios"], fmt(p.get("bootstrap_p_two_sided"), 4), fmt(p.get("holm_adjusted_p"), 4)])
    for key, lab in [("secondary_commercial_vs_neutral_explicit", "explicit goal"), ("secondary_moderation_ambiguous_minus_explicit", "moderation (amb − exp)"), ("h1_ambiguous_minus_explicit_all_arms", "H1 ambiguous − explicit")]:
        for o in ("clarification", "representation_error", "recommended_utility", "regret"):
            p = results[key][o]["pooled"]
            t3.append([f"{OUTCOME_LABEL[o]} — {lab}", ci(p), p["n_scenarios"], fmt(p.get("bootstrap_p_two_sided"), 4), "secondary"])
    write_table("table3_primary_results", ["Contrast / outcome", "Estimate [95% CI]", "Scenarios", "Bootstrap p", "Holm p"], t3,
                "Table 3. Primary (commercial − neutral, ambiguous goal; pooled equal model weights) and secondary matched contrasts")
    tm = []
    for o in prim:
        for m in SELECTED_MODELS:
            pa = prim[o]["by_model"][m]; pe = results["secondary_commercial_vs_neutral_explicit"][o]["by_model"][m]
            tm.append([OUTCOME_LABEL[o], MODEL_LABEL[m], ci(pa), ci(pe), pa["n_scenarios"]])
    write_table("table_model_specific_results", ["Outcome", "Model", "Commercial − neutral (ambiguous)", "Commercial − neutral (explicit)", "Scenarios"], tm,
                "Model-specific matched contrasts (95% scenario-bootstrap CIs)")
    t4 = []
    stab = results["repeat_stability"]
    for m in SELECTED_MODELS:
        s = stab[m]
        t4.append(["Repeat stability", MODEL_LABEL[m], f"clarification agree {fmt(s['clarification_decision_agreement'], 2)}; top product agree {fmt(s['top_product_agreement'], 2)}; weight spread mean {fmt(s['weight_spread_mean_max_pairwise_half_l1'], 3)}", "core"])
    for name, res in robust.items():
        for o in ("clarification", "representation_error", "recommended_utility", "regret"):
            p = res["primary_commercial_vs_neutral_ambiguous"][o]["pooled"]
            t4.append([name, OUTCOME_LABEL[o], ci(p), f"{res['n_valid_runs']}/{res['n_planned_runs']} valid"])
    write_table("table4_robustness_results", ["Check", "Outcome / model", "Result", "Runs"], t4, "Table 4. Robustness results")
    tax = results["failure_taxonomy"]
    t5 = [[c.replace("_", " "), tax["all"][c]["count"], fmt(tax["all"][c]["rate_over_planned"], 3)] + [tax[m][c]["count"] for m in SELECTED_MODELS] for c in tax["all"]]
    write_table("table5_failure_taxonomy", ["Category", "Count (all)", "Rate over planned", *[MODEL_LABEL[m] for m in SELECTED_MODELS]], t5,
                "Table 5. Failure taxonomy (pre-specified operational rules) and counts over 1,920 planned core runs")


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "core"
    rows = load_rows(stage)
    results = json.loads((ROOT / "artifacts" / "analysis" / f"{stage}_results.json").read_text(encoding="utf-8"))
    robust = {}
    for name, label in (("robust_template", "Robust: alternate template"), ("robust_order", "Robust: product order"), ("robust_cue_location", "Robust: cue location")):
        path = ROOT / "artifacts" / "analysis" / f"{name}_results.json"
        if path.exists():
            robust[label] = json.loads(path.read_text(encoding="utf-8"))
    fig1_framework(); fig2_pipeline()
    dot_panels(rows, "clarification", "Clarification rate", "fig3_clarification", (-0.05, 1.05))
    dot_panels(rows, "representation_error", "Representation error D", "fig4_representation_error")
    fig5_utility_regret(rows); fig6_forest(results, robust)
    example = fig7_failure_pathway(rows); fig8_d_vs_utility(rows)
    tables(results, robust, rows)
    (ROOT / "outputs" / "figure_provenance.json").write_text(json.dumps({"stage": stage, "dataset": f"data/analysis/{stage}_dataset.jsonl",
        "results": f"artifacts/analysis/{stage}_results.json", "robustness_included": list(robust), "fig7_selection": example}, indent=2) + "\n", encoding="utf-8")
    print("figures:", sorted(p.name for p in FIG.glob("*.png"))); print("tables:", sorted(p.name for p in TAB.glob("*.md")))


if __name__ == "__main__":
    main()
