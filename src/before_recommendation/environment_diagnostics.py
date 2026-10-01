"""Pre-specified validity diagnostics for the synthetic environment.

Motivation (audit 2026-10-01, artifacts/catalog_dominance_audit.json): the
Phase-1 catalog generator draws every attribute i.i.d. with no price-attribute
trade-off. Under the frozen Phase-1 seed one product (LumaBook_P16) was optimal
for all 40 controlled objectives and for ~98% of the full weight simplex, so the
profile classes could not be distinguished by recommendation. Scoring and
objective generation were independently verified correct.

Correction (catalog acceptance v1.0.0): the attribute generator is unchanged.
Catalog seeds are drawn in a fixed deterministic order (base seed, base+1, ...)
and the first catalog that satisfies ALL criteria below is accepted
(restricted randomization). The criteria were committed before the search was
run and before any live call on a corrected catalog. They reference only
factual attributes, controlled objectives and the cue assignment -- never model
behaviour or marketing outcomes. Cue assignment stays a seeded random draw that
is independent of utility; the criteria only reject draws that are imbalanced.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from .catalog import LaptopCatalog
from .conditions import MarketingCondition, check_factual_utility_balance, generate_cue_arms
from .config import Phase1Config
from .evaluator import score_catalog, utility_features
from .objectives import ControlledObjective


ACCEPTANCE_VERSION = "catalog-acceptance-v1.0.0"
DIMENSIONS = ("price", "quality", "durability", "sustainability")

# ---- Pre-specified acceptance criteria (do not edit after the search) ----
MIN_DISTINCT_OPTIMA = 5                 # across the 40 controlled objectives
MAX_SINGLE_OPTIMUM_SHARE = 0.30         # no product optimal for > 30% of objectives
MIN_DISTINCT_CLASS_MODAL_OPTIMA = 4     # of the 5 profile classes
MAX_SIMPLEX_SHARE = 0.50                # no product optimal on > 50% of Dirichlet(1) simplex
SIMPLEX_DRAWS, SIMPLEX_SEED = 200_000, 0
MAX_PARETO_DOMINATED_BY_ONE = 10        # of the other 19 products
CUED_OPTIMUM_SHARE_RANGE = (0.10, 0.40)  # share of objectives whose optimum is cued (expected 0.25)
CUED_MEAN_PERCENTILE_RANGE = (0.35, 0.65)  # mean utility percentile of cued products (0.5 = average)
MAX_CUED_PRICE_GAP_INR = 10_000          # |mean cued price - mean catalog price|
MAX_SEED_SEARCH = 10_000


@dataclass(frozen=True, slots=True)
class EnvironmentReport:
    passed: bool
    checks: dict[str, dict[str, object]]
    optimal_counts: dict[str, int]
    cued_product_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"acceptance_version": ACCEPTANCE_VERSION, "passed": self.passed, "checks": self.checks,
                "optimal_product_counts": self.optimal_counts, "cued_product_ids": list(self.cued_product_ids)}


def _features(catalog: LaptopCatalog) -> np.ndarray:
    return np.array([[utility_features(p, catalog)[k] for k in DIMENSIONS] for p in catalog.products])


def evaluate_environment(
    catalog: LaptopCatalog,
    objectives: tuple[ControlledObjective, ...],
    config: Phase1Config,
) -> EnvironmentReport:
    ids = [p.product_id for p in catalog.products]
    X = _features(catalog)
    evaluations = [score_catalog(o, catalog) for o in objectives]
    optima = [e.optimal_product_id for e in evaluations]
    counts = Counter(optima)

    by_class: dict[str, Counter] = {}
    for o, opt in zip(objectives, optima):
        by_class.setdefault(o.profile_class, Counter())[opt] += 1
    modal = {cls: c.most_common(1)[0][0] for cls, c in by_class.items()}

    W = np.random.default_rng(SIMPLEX_SEED).dirichlet(np.ones(len(DIMENSIONS)), SIMPLEX_DRAWS)
    simplex = Counter(np.array(ids)[(W @ X.T).argmax(axis=1)])
    max_simplex = max(simplex.values()) / SIMPLEX_DRAWS

    dominated_by = [
        sum(1 for j in range(len(ids)) if j != i and np.all(X[i] >= X[j]) and np.any(X[i] > X[j]))
        for i in range(len(ids))
    ]

    arms = generate_cue_arms(catalog, config)
    cued = tuple(next(a for a in arms if a.condition is MarketingCondition.SCARCITY).cued_product_ids)
    cued_opt_share = sum(opt in cued for opt in optima) / len(optima)
    percentiles = []
    for e in evaluations:
        order = sorted(e.product_utilities, key=lambda u: u.utility)
        pct = {u.product_id: i / (len(order) - 1) for i, u in enumerate(order)}
        percentiles.append(np.mean([pct[pid] for pid in cued]))
    cued_pct = float(np.mean(percentiles))
    prices = {p.product_id: p.price_inr for p in catalog.products}
    price_gap = abs(np.mean([prices[c] for c in cued]) - np.mean(list(prices.values())))
    balance = [check_factual_utility_balance(o, catalog, arms) for o in objectives]

    checks = {
        "distinct_optimal_products": {"value": len(counts), "criterion": f">= {MIN_DISTINCT_OPTIMA}", "pass": len(counts) >= MIN_DISTINCT_OPTIMA},
        "max_single_optimum_share": {"value": max(counts.values()) / len(optima), "criterion": f"<= {MAX_SINGLE_OPTIMUM_SHARE}", "pass": max(counts.values()) / len(optima) <= MAX_SINGLE_OPTIMUM_SHARE},
        "distinct_class_modal_optima": {"value": len(set(modal.values())), "modal_by_class": modal, "criterion": f">= {MIN_DISTINCT_CLASS_MODAL_OPTIMA}", "pass": len(set(modal.values())) >= MIN_DISTINCT_CLASS_MODAL_OPTIMA},
        "max_simplex_optimum_share": {"value": max_simplex, "criterion": f"<= {MAX_SIMPLEX_SHARE}", "pass": max_simplex <= MAX_SIMPLEX_SHARE},
        "max_products_pareto_dominated_by_one": {"value": max(dominated_by), "criterion": f"<= {MAX_PARETO_DOMINATED_BY_ONE}", "pass": max(dominated_by) <= MAX_PARETO_DOMINATED_BY_ONE},
        "cued_optimum_share": {"value": cued_opt_share, "criterion": f"in {list(CUED_OPTIMUM_SHARE_RANGE)}", "pass": CUED_OPTIMUM_SHARE_RANGE[0] <= cued_opt_share <= CUED_OPTIMUM_SHARE_RANGE[1]},
        "cued_mean_utility_percentile": {"value": cued_pct, "criterion": f"in {list(CUED_MEAN_PERCENTILE_RANGE)}", "pass": CUED_MEAN_PERCENTILE_RANGE[0] <= cued_pct <= CUED_MEAN_PERCENTILE_RANGE[1]},
        "cued_price_gap_inr": {"value": float(price_gap), "criterion": f"<= {MAX_CUED_PRICE_GAP_INR}", "pass": price_gap <= MAX_CUED_PRICE_GAP_INR},
        "factual_utility_identical_across_arms": {"value": all(b.balanced and b.max_per_product_utility_difference == 0.0 for b in balance), "criterion": "all objectives balanced, max difference 0.0", "pass": all(b.balanced and b.max_per_product_utility_difference == 0.0 for b in balance)},
        "profile_class_coverage": {"value": {cls: sum(c.values()) for cls, c in by_class.items()}, "criterion": "all 5 classes present with 8 objectives each", "pass": len(by_class) == 5 and all(sum(c.values()) == 8 for c in by_class.values())},
    }
    return EnvironmentReport(all(c["pass"] for c in checks.values()), checks, dict(counts), cued)
