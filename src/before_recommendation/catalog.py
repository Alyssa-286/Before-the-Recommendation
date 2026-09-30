"""Synthetic factual laptop catalog generation.

Storefront marketing cues are intentionally absent here. They will be added as
condition-specific presentation overlays, leaving these records unchanged.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import random

from .config import Phase1Config, load_phase1_config


CATALOG_GENERATOR_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class Laptop:
    product_id: str
    price_inr: int
    quality: int
    durability: int
    repairability: int
    sustainability: int
    battery_life: int
    brand_familiarity: int
    popularity: int


@dataclass(frozen=True, slots=True)
class LaptopCatalog:
    products: tuple[Laptop, ...]
    seed: int
    generator_version: str
    config_sha256: str
    price_min_inr: int
    price_max_inr: int

    def get(self, product_id: str) -> Laptop:
        for product in self.products:
            if product.product_id == product_id:
                return product
        raise KeyError(f"Unknown product id: {product_id}")


def generate_catalog(
    config: Phase1Config | None = None,
    *,
    seed: int | None = None,
    count: int | None = None,
) -> LaptopCatalog:
    """Generate a repeatable set of synthetic laptop facts from a local RNG."""
    config = config or load_phase1_config()
    actual_seed = config.catalog_seed if seed is None else seed
    actual_count = config.catalog_count if count is None else count
    if actual_count < 1:
        raise ValueError("Catalog count must be positive.")

    rng = random.Random(actual_seed)
    price_steps = (config.price_max_inr - config.price_min_inr) // config.price_step_inr
    products = []
    for index in range(1, actual_count + 1):
        price = config.price_min_inr + rng.randint(0, price_steps) * config.price_step_inr
        scores = [rng.randint(config.score_min, config.score_max) for _ in range(7)]
        products.append(
            Laptop(
                product_id=f"LumaBook_P{index:02d}",
                price_inr=price,
                quality=scores[0],
                durability=scores[1],
                repairability=scores[2],
                sustainability=scores[3],
                battery_life=scores[4],
                brand_familiarity=scores[5],
                popularity=scores[6],
            )
        )

    return LaptopCatalog(
        products=tuple(products),
        seed=actual_seed,
        generator_version=CATALOG_GENERATOR_VERSION,
        config_sha256=config.config_sha256,
        price_min_inr=config.price_min_inr,
        price_max_inr=config.price_max_inr,
    )


def catalog_fingerprint(catalog: LaptopCatalog) -> str:
    """Hash catalog facts and generation metadata in a stable JSON encoding."""
    payload = {
        "products": [asdict(product) for product in catalog.products],
        "seed": catalog.seed,
        "generator_version": catalog.generator_version,
        "config_sha256": catalog.config_sha256,
        "price_min_inr": catalog.price_min_inr,
        "price_max_inr": catalog.price_max_inr,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
