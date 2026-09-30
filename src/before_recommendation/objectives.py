"""Controlled, synthetic latent-objective generation."""

from __future__ import annotations

from dataclasses import dataclass
import random

from .config import Phase1Config, load_phase1_config


OBJECTIVE_GENERATOR_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ControlledObjective:
    """A synthetic evaluation target, not a claim about a human's preferences."""

    objective_id: str
    profile_class: str
    weights: tuple[tuple[str, float], ...]
    seed: int
    generator_version: str
    config_sha256: str
    hard_max_price_inr: int | None = None
    budget_reference_inr: int | None = None

    def as_dict(self) -> dict[str, float]:
        return dict(self.weights)

    def weight(self, dimension: str) -> float:
        try:
            return dict(self.weights)[dimension]
        except KeyError as exc:
            raise KeyError(f"Unknown objective dimension: {dimension}") from exc


def generate_objectives(
    config: Phase1Config | None = None,
    *,
    seed: int | None = None,
    count: int | None = None,
) -> tuple[ControlledObjective, ...]:
    """Create balanced, jittered objective vectors reproducibly."""
    config = config or load_phase1_config()
    actual_seed = config.objectives_seed if seed is None else seed
    actual_count = config.objective_count if count is None else count
    if actual_count < 1:
        raise ValueError("Objective count must be positive.")

    rng = random.Random(actual_seed)
    templates = config.profile_templates()
    class_names = [templates[index % len(templates)][0] for index in range(actual_count)]
    rng.shuffle(class_names)
    template_by_name = dict(templates)

    objectives = []
    for index, class_name in enumerate(class_names, start=1):
        center = template_by_name[class_name]
        perturbed = [
            max(0.0, weight + rng.uniform(-config.objective_jitter, config.objective_jitter))
            for weight in center
        ]
        total = sum(perturbed)
        normalized = [round(value / total, 10) for value in perturbed[:-1]]
        normalized.append(round(1.0 - sum(normalized), 10))
        objectives.append(
            ControlledObjective(
                objective_id=f"OBJECTIVE_{index:03d}",
                profile_class=class_name,
                weights=tuple(zip(config.objective_dimensions, normalized, strict=True)),
                seed=actual_seed,
                generator_version=OBJECTIVE_GENERATOR_VERSION,
                config_sha256=config.config_sha256,
                hard_max_price_inr=config.hard_max_price_inr,
                budget_reference_inr=config.explicit_budget_reference_inr,
            )
        )
    return tuple(objectives)
