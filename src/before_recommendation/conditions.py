"""Condition-specific marketing overlays and factual-utility balance audit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import random

from .catalog import Laptop, LaptopCatalog
from .config import Phase1Config, load_phase1_config
from .evaluator import product_utility
from .objectives import ControlledObjective


CUE_GENERATOR_VERSION = "1.0.0"


class MarketingCondition(StrEnum):
    NEUTRAL = "neutral"
    SCARCITY = "scarcity"
    SOCIAL_PROOF = "social_proof"
    DISCOUNT = "discount"


_CUE_LABELS = {
    MarketingCondition.SCARCITY: "Only 2 units remaining.",
    MarketingCondition.SOCIAL_PROOF: "50,000+ students chose this.",
    MarketingCondition.DISCOUNT: "20% promotional discount.",
}


@dataclass(frozen=True, slots=True)
class ProductListing:
    product: Laptop
    marketing_label: str | None


@dataclass(frozen=True, slots=True)
class CueArm:
    condition: MarketingCondition
    listings: tuple[ProductListing, ...]
    cued_product_ids: tuple[str, ...]
    seed: int
    generator_version: str
    config_sha256: str


@dataclass(frozen=True, slots=True)
class CueBalanceReport:
    balanced: bool
    condition_means: tuple[tuple[str, float], ...]
    max_per_product_utility_difference: float
    cue_sets_match: bool
    factual_records_match_catalog: bool
    reason: str


def generate_cue_arms(
    catalog: LaptopCatalog,
    config: Phase1Config | None = None,
    *,
    seed: int | None = None,
    cued_fraction: float | None = None,
) -> tuple[CueArm, ...]:
    """Overlay marketing labels without modifying any factual product field."""
    config = config or load_phase1_config()
    actual_seed = config.cues_seed if seed is None else seed
    fraction = config.cued_fraction if cued_fraction is None else cued_fraction
    if not 0 <= fraction <= 1:
        raise ValueError("cued_fraction must be in [0, 1].")
    ids = sorted(product.product_id for product in catalog.products)
    if not ids:
        raise ValueError("Cannot create cue arms for an empty catalog.")

    cue_count = min(len(ids), math.ceil(len(ids) * fraction)) if fraction else 0
    selected_ids = tuple(sorted(random.Random(actual_seed).sample(ids, cue_count)))
    arms = []
    for condition in MarketingCondition:
        label = _CUE_LABELS.get(condition)
        listings = tuple(
            ProductListing(
                product=product,
                marketing_label=(label if product.product_id in selected_ids else None),
            )
            for product in catalog.products
        )
        arms.append(
            CueArm(
                condition=condition,
                listings=listings,
                cued_product_ids=selected_ids if condition is not MarketingCondition.NEUTRAL else (),
                seed=actual_seed,
                generator_version=CUE_GENERATOR_VERSION,
                config_sha256=config.config_sha256,
            )
        )
    return tuple(arms)


def check_factual_utility_balance(
    objective: ControlledObjective,
    catalog: LaptopCatalog,
    arms: tuple[CueArm, ...],
    *,
    tolerance: float = 1e-12,
) -> CueBalanceReport:
    """Confirm factual product utility is identical across marketing arms."""
    if not arms:
        raise ValueError("At least one cue arm is required.")
    base_products = {product.product_id: product for product in catalog.products}
    base_utilities = {
        product_id: product_utility(product, objective, catalog)
        for product_id, product in base_products.items()
    }
    condition_means: list[tuple[str, float]] = []
    observed_maps: list[dict[str, float]] = []
    facts_match = True
    assignments_valid = True

    for arm in arms:
        arm_products = {listing.product.product_id: listing.product for listing in arm.listings}
        if len(arm_products) != len(arm.listings) or arm_products.keys() != base_products.keys():
            facts_match = False
            observed_maps.append({})
            condition_means.append((arm.condition.value, float("nan")))
            continue
        if any(arm_products[key] != base_products[key] for key in base_products):
            facts_match = False
        expected_label = _CUE_LABELS.get(arm.condition)
        expected_cued_ids = set(arm.cued_product_ids)
        actual_cued_ids = {
            listing.product.product_id
            for listing in arm.listings
            if listing.marketing_label is not None
        }
        if actual_cued_ids != expected_cued_ids or any(
            listing.marketing_label
            != (expected_label if listing.product.product_id in expected_cued_ids else None)
            for listing in arm.listings
        ):
            assignments_valid = False
        utility_map = {
            product_id: product_utility(product, objective, catalog)
            for product_id, product in arm_products.items()
        }
        observed_maps.append(utility_map)
        condition_means.append((arm.condition.value, sum(utility_map.values()) / len(utility_map)))

    max_difference = max(
        (
            abs(value - base_utilities[product_id])
            for utility_map in observed_maps
            for product_id, value in utility_map.items()
            if product_id in base_utilities
        ),
        default=float("inf") if not facts_match else 0.0,
    )
    cue_sets = [set(arm.cued_product_ids) for arm in arms if arm.condition is not MarketingCondition.NEUTRAL]
    cue_sets_match = (
        bool(cue_sets)
        and all(cue_set == cue_sets[0] for cue_set in cue_sets)
        and assignments_valid
    )
    balanced = (
        facts_match
        and max_difference <= tolerance
        and cue_sets_match
        and all(math.isclose(mean, condition_means[0][1], abs_tol=tolerance) for _, mean in condition_means)
    )
    reason = (
        "Every arm contains the same factual records and per-product utility; cue assignment is matched across commercial arms."
        if balanced
        else "Cue-arm records, per-product utility, or cue assignment differ; inspect the returned balance diagnostics."
    )
    return CueBalanceReport(
        balanced=balanced,
        condition_means=tuple(condition_means),
        max_per_product_utility_difference=max_difference,
        cue_sets_match=cue_sets_match,
        factual_records_match_catalog=facts_match,
        reason=reason,
    )
