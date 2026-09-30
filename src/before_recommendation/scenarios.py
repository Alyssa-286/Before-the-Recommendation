"""Reproducible scenario bundles and stripped agent-facing views."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .catalog import LaptopCatalog, catalog_fingerprint, generate_catalog
from .conditions import MarketingCondition, ProductListing, generate_cue_arms
from .config import Phase1Config, load_phase1_config
from .objectives import ControlledObjective, generate_objectives
from .prompts import GoalCondition, generate_request


SCENARIO_GENERATOR_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class AgentScenarioView:
    """Only the user request and storefront listings intended for an agent."""

    scenario_id: str
    goal_condition: GoalCondition
    marketing_condition: MarketingCondition
    user_request: str
    listings: tuple[ProductListing, ...]


@dataclass(frozen=True, slots=True)
class ResearchScenario:
    """Research-side bundle containing the hidden controlled objective."""

    scenario_id: str
    objective: ControlledObjective
    catalog: LaptopCatalog
    config: Phase1Config

    def agent_view(
        self,
        goal_condition: GoalCondition | str,
        marketing_condition: MarketingCondition | str,
    ) -> AgentScenarioView:
        goal = GoalCondition(goal_condition)
        marketing = MarketingCondition(marketing_condition)
        request = generate_request(self.objective, goal)
        arm = next(
            cue_arm
            for cue_arm in generate_cue_arms(self.catalog, self.config)
            if cue_arm.condition is marketing
        )
        return AgentScenarioView(
            scenario_id=self.scenario_id,
            goal_condition=goal,
            marketing_condition=marketing,
            user_request=request.text,
            listings=arm.listings,
        )


def generate_scenarios(config: Phase1Config | None = None) -> tuple[ResearchScenario, ...]:
    """Create the frozen catalog and a balanced set of controlled objectives."""
    config = config or load_phase1_config()
    catalog = generate_catalog(config)
    objectives = generate_objectives(config)
    return tuple(
        ResearchScenario(
            scenario_id=f"SCENARIO_{index:03d}",
            objective=objective,
            catalog=catalog,
            config=config,
        )
        for index, objective in enumerate(objectives, start=1)
    )


def scenario_fingerprint(scenario: ResearchScenario) -> str:
    """Hash hidden objective, factual catalog, and source config provenance."""
    payload = {
        "scenario_id": scenario.scenario_id,
        "objective_id": scenario.objective.objective_id,
        "profile_class": scenario.objective.profile_class,
        "weights": scenario.objective.weights,
        "hard_max_price_inr": scenario.objective.hard_max_price_inr,
        "budget_reference_inr": scenario.objective.budget_reference_inr,
        "objective_seed": scenario.objective.seed,
        "objective_generator_version": scenario.objective.generator_version,
        "catalog_fingerprint": catalog_fingerprint(scenario.catalog),
        "scenario_generator_version": SCENARIO_GENERATOR_VERSION,
        "config_sha256": scenario.config.config_sha256,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
