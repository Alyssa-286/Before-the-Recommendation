"""Loading and validating the versioned Phase 1 configuration."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "phase1.json"
)


@dataclass(frozen=True, slots=True)
class Phase1Config:
    schema_version: str
    experiment_version: str
    config_sha256: str
    catalog_seed: int
    objectives_seed: int
    cues_seed: int
    catalog_count: int
    price_min_inr: int
    price_max_inr: int
    price_step_inr: int
    score_min: int
    score_max: int
    objective_count: int
    objective_jitter: float
    hard_max_price_inr: int | None
    explicit_budget_reference_inr: int
    cued_fraction: float
    objective_dimensions: tuple[str, ...]
    profile_classes: tuple[tuple[str, tuple[float, ...]], ...]

    def profile_templates(self) -> tuple[tuple[str, tuple[float, ...]], ...]:
        return self.profile_classes


def load_phase1_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Phase1Config:
    """Read the config and retain a digest of its exact source bytes."""
    config_path = Path(path)
    raw = config_path.read_bytes()
    payload: dict[str, Any] = json.loads(raw)

    dimensions = tuple(payload["objectives"]["dimensions"])
    classes = tuple(
        (
            name,
            tuple(float(profile[name]) for name in dimensions),
        )
        for name, profile in payload["objectives"]["profile_classes"].items()
    )
    config = Phase1Config(
        schema_version=payload["schema_version"],
        experiment_version=payload["experiment_version"],
        config_sha256=hashlib.sha256(raw).hexdigest(),
        catalog_seed=int(payload["seeds"]["catalog"]),
        objectives_seed=int(payload["seeds"]["objectives"]),
        cues_seed=int(payload["seeds"]["cues"]),
        catalog_count=int(payload["catalog"]["count"]),
        price_min_inr=int(payload["catalog"]["price_min_inr"]),
        price_max_inr=int(payload["catalog"]["price_max_inr"]),
        price_step_inr=int(payload["catalog"]["price_step_inr"]),
        score_min=int(payload["catalog"]["score_min"]),
        score_max=int(payload["catalog"]["score_max"]),
        objective_count=int(payload["objectives"]["count"]),
        objective_jitter=float(payload["objectives"]["jitter"]),
        hard_max_price_inr=(
            None
            if payload["objectives"].get("hard_max_price_inr") is None
            else int(payload["objectives"]["hard_max_price_inr"])
        ),
        explicit_budget_reference_inr=int(payload["prompts"]["explicit_budget_reference_inr"]),
        cued_fraction=float(payload["cues"]["fraction"]),
        objective_dimensions=dimensions,
        profile_classes=classes,
    )
    _validate_config(config)
    return config


def _validate_config(config: Phase1Config) -> None:
    if not config.schema_version or not config.experiment_version:
        raise ValueError("Configuration versions must be non-empty.")
    if config.catalog_count < 1 or config.objective_count < 1:
        raise ValueError("Catalog and objective counts must be positive.")
    if config.price_min_inr >= config.price_max_inr:
        raise ValueError("price_min_inr must be less than price_max_inr.")
    if config.price_step_inr < 1:
        raise ValueError("price_step_inr must be positive.")
    if (config.price_max_inr - config.price_min_inr) % config.price_step_inr:
        raise ValueError("Price range must be divisible by price_step_inr.")
    if not 0 <= config.score_min <= config.score_max <= 100:
        raise ValueError("Catalog scores must be between 0 and 100.")
    if not 0 <= config.objective_jitter < 1:
        raise ValueError("objective_jitter must be in [0, 1).")
    if config.hard_max_price_inr is not None and config.hard_max_price_inr < 0:
        raise ValueError("hard_max_price_inr must be non-negative.")
    if config.explicit_budget_reference_inr < 0:
        raise ValueError("explicit_budget_reference_inr must be non-negative.")
    if not 0 <= config.cued_fraction <= 1:
        raise ValueError("cued_fraction must be in [0, 1].")
    if not config.objective_dimensions or not config.profile_classes:
        raise ValueError("At least one objective dimension and profile class are required.")

    expected = set(config.objective_dimensions)
    for class_name, weights in config.profile_classes:
        if len(weights) != len(config.objective_dimensions):
            raise ValueError(f"Profile class {class_name!r} has the wrong number of weights.")
        if any(weight < 0 for weight in weights):
            raise ValueError(f"Profile class {class_name!r} has a negative weight.")
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError(f"Profile class {class_name!r} weights must sum to 1.")
    if expected != {"price", "quality", "durability", "sustainability"}:
        raise ValueError("The locked objective dimensions are price, quality, durability, and sustainability.")
