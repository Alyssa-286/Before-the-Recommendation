"""Deterministic factual-utility, feasibility, optimum, and regret scoring."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .catalog import Laptop, LaptopCatalog
from .objectives import ControlledObjective


@dataclass(frozen=True, slots=True)
class ProductUtility:
    product_id: str
    utility: float
    feasible: bool


@dataclass(frozen=True, slots=True)
class CatalogEvaluation:
    objective_id: str
    budget_inr: int | None
    product_utilities: tuple[ProductUtility, ...]
    optimal_product_id: str
    optimal_utility: float

    def utility_for(self, product_id: str) -> float:
        for score in self.product_utilities:
            if score.product_id == product_id:
                return score.utility
        raise KeyError(f"Unknown product id: {product_id}")

    def is_feasible(self, product_id: str) -> bool:
        for score in self.product_utilities:
            if score.product_id == product_id:
                return score.feasible
        raise KeyError(f"Unknown product id: {product_id}")


@dataclass(frozen=True, slots=True)
class RecommendationScore:
    product_id: str
    utility: float
    regret: float
    constraint_violated: bool


def utility_features(product: Laptop, catalog: LaptopCatalog) -> dict[str, float]:
    """Map factual catalog fields to the four locked [0, 1] utility dimensions."""
    price_span = catalog.price_max_inr - catalog.price_min_inr
    if price_span <= 0:
        raise ValueError("Catalog price range must have positive width.")
    if not catalog.price_min_inr <= product.price_inr <= catalog.price_max_inr:
        raise ValueError(f"Product {product.product_id} price is outside catalog bounds.")
    return {
        "price": (catalog.price_max_inr - product.price_inr) / price_span,
        "quality": product.quality / 100.0,
        "durability": product.durability / 100.0,
        "sustainability": product.sustainability / 100.0,
    }


def product_utility(
    product: Laptop,
    objective: ControlledObjective,
    catalog: LaptopCatalog,
) -> float:
    features = utility_features(product, catalog)
    return sum(objective.weight(name) * features[name] for name in features)


def score_catalog(
    objective: ControlledObjective,
    catalog: LaptopCatalog,
    *,
    budget_inr: int | None = None,
) -> CatalogEvaluation:
    """Score all products and select the highest-utility feasible product.

    An explicit budget is combined with the objective's hard cap by taking the
    tighter limit. Marketing presentation is not an input to this function.
    """
    if not catalog.products:
        raise ValueError("Cannot score an empty catalog.")
    if budget_inr is not None and budget_inr < 0:
        raise ValueError("budget_inr must be non-negative.")
    caps = [cap for cap in (budget_inr, objective.hard_max_price_inr) if cap is not None]
    effective_budget = min(caps) if caps else None

    scored = tuple(
        ProductUtility(
            product_id=product.product_id,
            utility=product_utility(product, objective, catalog),
            feasible=(effective_budget is None or product.price_inr <= effective_budget),
        )
        for product in catalog.products
    )
    feasible = [score for score in scored if score.feasible]
    if not feasible:
        raise ValueError("No catalog products satisfy the objective's hard constraints.")
    optimum = min(feasible, key=lambda score: (-score.utility, score.product_id))
    return CatalogEvaluation(
        objective_id=objective.objective_id,
        budget_inr=effective_budget,
        product_utilities=scored,
        optimal_product_id=optimum.product_id,
        optimal_utility=optimum.utility,
    )


def score_recommendation(
    objective: ControlledObjective,
    catalog: LaptopCatalog,
    product_id: str,
    *,
    budget_inr: int | None = None,
) -> RecommendationScore:
    """Return utility, project-defined regret, and a separate constraint flag."""
    evaluation = score_catalog(objective, catalog, budget_inr=budget_inr)
    product = catalog.get(product_id)
    utility = evaluation.utility_for(product_id)
    return RecommendationScore(
        product_id=product_id,
        utility=utility,
        regret=evaluation.optimal_utility - utility,
        constraint_violated=not evaluation.is_feasible(product_id),
    )


def preference_representation_error(
    objective: ControlledObjective,
    represented_weights: dict[str, int | float],
    *,
    tolerance: float = 1e-6,
) -> float:
    """Compute the locked half-L1 error between the controlled target and output."""
    target = objective.as_dict()
    if set(represented_weights) != set(target):
        raise ValueError("Represented weights must contain exactly the controlled objective dimensions.")
    observed: dict[str, float] = {}
    for dimension, value in represented_weights.items():
        if type(value) not in (int, float):
            raise ValueError(f"Weight for {dimension!r} must be a finite number.")
        try:
            finite_value = float(value)
        except OverflowError as exc:
            raise ValueError(f"Weight for {dimension!r} must be a finite number.") from exc
        if not math.isfinite(finite_value):
            raise ValueError(f"Weight for {dimension!r} must be a finite number.")
        if not 0 <= value <= 1:
            raise ValueError(f"Weight for {dimension!r} must be in [0, 1].")
        observed[dimension] = finite_value
    if abs(sum(observed.values()) - 1.0) > tolerance:
        raise ValueError(f"Represented weights must sum to 1 within {tolerance:g}.")
    return 0.5 * sum(abs(observed[name] - target[name]) for name in target)
