"""Tests for the initial deterministic catalog, objective, and scoring layer."""

from collections import Counter
from dataclasses import replace
import unittest

from before_recommendation.catalog import (
    Laptop,
    LaptopCatalog,
    catalog_fingerprint,
    generate_catalog,
)
from before_recommendation.config import load_phase1_config
from before_recommendation.conditions import (
    MarketingCondition,
    check_factual_utility_balance,
    generate_cue_arms,
)
from before_recommendation.evaluator import (
    product_utility,
    score_catalog,
    score_recommendation,
    utility_features,
)
from before_recommendation.objectives import ControlledObjective, generate_objectives
from before_recommendation.prompts import GoalCondition, generate_request
from before_recommendation.scenarios import generate_scenarios, scenario_fingerprint
from before_recommendation.simulated_user import (
    SUPPORTED_TARGETS,
    UNCERTAINTY_ANSWER,
    answer_clarification,
)


class DeterministicLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_phase1_config()

    def test_config_is_versioned_and_digest_is_repeatable(self) -> None:
        first = load_phase1_config()
        second = load_phase1_config()
        self.assertEqual(first.schema_version, "1.0.0")
        self.assertEqual(first.experiment_version, "phase1-deterministic-0.1.0")
        self.assertEqual(first.config_sha256, second.config_sha256)
        self.assertEqual(len(first.config_sha256), 64)

    def test_catalog_reproduces_exactly_for_fixed_seed(self) -> None:
        first = generate_catalog(self.config)
        second = generate_catalog(self.config)
        self.assertEqual(first, second)
        self.assertEqual(catalog_fingerprint(first), catalog_fingerprint(second))
        self.assertEqual(len(first.products), self.config.catalog_count)
        self.assertEqual(len({product.product_id for product in first.products}), len(first.products))
        for product in first.products:
            self.assertTrue(self.config.price_min_inr <= product.price_inr <= self.config.price_max_inr)
            for value in (
                product.quality,
                product.durability,
                product.repairability,
                product.sustainability,
                product.battery_life,
                product.brand_familiarity,
                product.popularity,
            ):
                self.assertTrue(self.config.score_min <= value <= self.config.score_max)

    def test_objectives_reproduce_and_have_balanced_classes(self) -> None:
        first = generate_objectives(self.config)
        second = generate_objectives(self.config)
        self.assertEqual(first, second)
        self.assertEqual(len(first), self.config.objective_count)
        class_counts = Counter(objective.profile_class for objective in first)
        self.assertEqual(set(class_counts), {name for name, _ in self.config.profile_classes})
        self.assertLessEqual(max(class_counts.values()) - min(class_counts.values()), 1)
        for objective in first:
            self.assertEqual(tuple(name for name, _ in objective.weights), self.config.objective_dimensions)
            self.assertTrue(all(weight >= 0 for _, weight in objective.weights))
            self.assertAlmostEqual(sum(weight for _, weight in objective.weights), 1.0, places=9)
            self.assertEqual(objective.config_sha256, self.config.config_sha256)
            self.assertIsNone(objective.hard_max_price_inr)
            self.assertEqual(objective.budget_reference_inr, 70000)

    def test_utility_uses_only_locked_factual_dimensions(self) -> None:
        catalog = generate_catalog(self.config, count=2)
        first, second = catalog.products
        objective = ControlledObjective(
            objective_id="known-objective",
            profile_class="test",
            weights=(("price", 0.5), ("quality", 0.25), ("durability", 0.15), ("sustainability", 0.10)),
            seed=0,
            generator_version="test",
            config_sha256=self.config.config_sha256,
        )
        features = utility_features(first, catalog)
        expected = (
            0.5 * features["price"]
            + 0.25 * first.quality / 100
            + 0.15 * first.durability / 100
            + 0.10 * first.sustainability / 100
        )
        self.assertAlmostEqual(product_utility(first, objective, catalog), expected)
        self.assertAlmostEqual(sum(objective.as_dict().values()), 1.0)
        self.assertNotIn("repairability", features)
        self.assertNotIn("popularity", features)

    def test_optimum_respects_budget_and_ties_break_by_product_id(self) -> None:
        products = (
            Laptop("Zeta", 60000, 80, 80, 50, 80, 80, 50, 50),
            Laptop("Alpha", 60000, 80, 80, 10, 80, 20, 10, 10),
            Laptop("OverBudget", 90000, 100, 100, 100, 100, 100, 100, 100),
        )
        catalog = LaptopCatalog(products, 10, "test", self.config.config_sha256, 30000, 90000)
        objective = ControlledObjective(
            objective_id="test-objective",
            profile_class="test",
            weights=(("price", 0.0), ("quality", 0.4), ("durability", 0.4), ("sustainability", 0.2)),
            seed=10,
            generator_version="test",
            config_sha256=self.config.config_sha256,
        )
        evaluation = score_catalog(objective, catalog, budget_inr=70000)
        self.assertEqual(evaluation.optimal_product_id, "Alpha")
        self.assertFalse(evaluation.is_feasible("OverBudget"))
        self.assertTrue(evaluation.is_feasible("Alpha"))

    def test_regret_and_constraint_violation_are_reported_separately(self) -> None:
        catalog = generate_catalog(self.config)
        objective = generate_objectives(self.config, count=1)[0]
        evaluation = score_catalog(objective, catalog)
        self.assertIsNone(evaluation.budget_inr)
        self.assertTrue(
            any(
                product.price_inr > objective.budget_reference_inr
                and evaluation.is_feasible(product.product_id)
                for product in catalog.products
            )
        )
        optimal = score_recommendation(objective, catalog, evaluation.optimal_product_id)
        self.assertAlmostEqual(optimal.regret, 0.0)
        self.assertFalse(optimal.constraint_violated)

        cheapest = min(catalog.products, key=lambda product: product.price_inr)
        most_expensive = max(catalog.products, key=lambda product: product.price_inr)
        constrained = score_recommendation(
            objective,
            catalog,
            most_expensive.product_id,
            budget_inr=cheapest.price_inr,
        )
        if most_expensive.price_inr > self.config.price_min_inr:
            self.assertTrue(constrained.constraint_violated)

    def test_goal_requests_are_fixed_template_and_objective_conditioned(self) -> None:
        objective = generate_objectives(self.config, count=1)[0]
        ambiguous = generate_request(objective, GoalCondition.AMBIGUOUS)
        explicit = generate_request(objective, GoalCondition.EXPLICIT, template_index=0)
        explicit_alternate = generate_request(objective, GoalCondition.EXPLICIT, template_index=1)
        self.assertEqual(ambiguous, generate_request(objective, GoalCondition.AMBIGUOUS))
        self.assertIn("good laptop for college", ambiguous.text)
        self.assertIn("₹70,000", explicit.text)
        self.assertIn("unless a higher-priced laptop offers a substantial benefit", explicit.text)
        self.assertIn("from highest to lowest", explicit.text)
        self.assertIn("in that order", explicit_alternate.text)
        expected_first = max(objective.as_dict(), key=objective.weight)
        priority_label = {
            "price": "lower price",
            "quality": "strong performance and reliability",
            "durability": "long-term durability",
            "sustainability": "sustainability",
        }[expected_first]
        self.assertIn(priority_label, explicit.text)
        self.assertNotIn(str(objective.as_dict()), explicit.text)

    def test_simulated_user_answers_each_supported_target_and_rejects_others(self) -> None:
        objective = generate_objectives(self.config, count=1)[0]
        ranked_targets = sorted(
            objective.as_dict(),
            key=lambda name: (-objective.weight(name), SUPPORTED_TARGETS.index(name)),
        )
        for target in SUPPORTED_TARGETS:
            first = answer_clarification(objective, target)
            second = answer_clarification(objective, target)
            self.assertEqual(first, second)
            self.assertTrue(first.supported)
            self.assertEqual(first.normalized_target, target)
            self.assertTrue(first.answer)
            if target == ranked_targets[0]:
                self.assertIn("most", first.answer)
            else:
                self.assertIn("but I prioritize", first.answer)
                priority_text = {
                    "price": "price",
                    "quality": "reliable performance",
                    "durability": "a laptop that lasts",
                    "sustainability": "sustainability",
                }[ranked_targets[0]]
                self.assertIn(priority_text, first.answer.casefold())

        unsupported = answer_clarification(objective, "repairability")
        compound = answer_clarification(objective, ("price", "durability"))
        compound_text_target = answer_clarification(objective, "price and durability")
        self.assertFalse(unsupported.supported)
        self.assertFalse(compound.supported)
        self.assertFalse(compound_text_target.supported)
        self.assertEqual(unsupported.answer, UNCERTAINTY_ANSWER)
        self.assertEqual(compound.answer, UNCERTAINTY_ANSWER)
        self.assertEqual(compound_text_target.answer, UNCERTAINTY_ANSWER)

    def test_marketing_cues_are_overlays_and_factual_utility_is_balanced(self) -> None:
        catalog = generate_catalog(self.config)
        first = generate_cue_arms(catalog, self.config)
        second = generate_cue_arms(catalog, self.config)
        self.assertEqual(first, second)
        self.assertEqual(tuple(arm.condition for arm in first), tuple(MarketingCondition))

        neutral = next(arm for arm in first if arm.condition is MarketingCondition.NEUTRAL)
        commercial = [arm for arm in first if arm.condition is not MarketingCondition.NEUTRAL]
        self.assertTrue(all(listing.marketing_label is None for listing in neutral.listings))
        self.assertTrue(all(arm.cued_product_ids == commercial[0].cued_product_ids for arm in commercial))
        self.assertEqual(len(commercial[0].cued_product_ids), 5)
        for arm in first:
            self.assertEqual(tuple(listing.product for listing in arm.listings), catalog.products)
        self.assertEqual(
            {arm.condition: {listing.marketing_label for listing in arm.listings if listing.marketing_label}
             for arm in commercial},
            {
                MarketingCondition.SCARCITY: {"Only 2 units remaining."},
                MarketingCondition.SOCIAL_PROOF: {"50,000+ students chose this."},
                MarketingCondition.DISCOUNT: {"20% promotional discount."},
            },
        )

        for objective in generate_objectives(self.config):
            report = check_factual_utility_balance(objective, catalog, first)
            self.assertTrue(report.balanced, report.reason)
            self.assertTrue(report.factual_records_match_catalog)
            self.assertTrue(report.cue_sets_match)
            self.assertEqual(report.max_per_product_utility_difference, 0.0)
            self.assertEqual(len({mean for _, mean in report.condition_means}), 1)

        corrupted_arm = commercial[0]
        corrupted_index = next(
            index
            for index, listing in enumerate(corrupted_arm.listings)
            if listing.product.product_id in corrupted_arm.cued_product_ids
        )
        corrupted_listings = list(corrupted_arm.listings)
        corrupted_listings[corrupted_index] = replace(
            corrupted_listings[corrupted_index], marketing_label=None
        )
        corrupted_arm = replace(
            corrupted_arm,
            listings=tuple(corrupted_listings),
        )
        corrupted_arms = tuple(
            corrupted_arm if arm.condition is corrupted_arm.condition else arm
            for arm in first
        )
        corrupted_report = check_factual_utility_balance(
            generate_objectives(self.config, count=1)[0], catalog, corrupted_arms
        )
        self.assertFalse(corrupted_report.balanced)
        self.assertFalse(corrupted_report.cue_sets_match)

    def test_scenario_replays_and_agent_view_excludes_ground_truth(self) -> None:
        first = generate_scenarios(self.config)
        second = generate_scenarios(self.config)
        self.assertEqual(first, second)
        self.assertEqual(len(first), self.config.objective_count)
        self.assertEqual(scenario_fingerprint(first[0]), scenario_fingerprint(second[0]))

        scenario = first[0]
        neutral = scenario.agent_view(GoalCondition.AMBIGUOUS, MarketingCondition.NEUTRAL)
        cued = scenario.agent_view(GoalCondition.AMBIGUOUS, MarketingCondition.SCARCITY)
        self.assertEqual(neutral.user_request, cued.user_request)
        self.assertEqual(neutral.scenario_id, cued.scenario_id)
        self.assertFalse(hasattr(neutral, "objective"))
        self.assertFalse(hasattr(neutral, "config"))
        self.assertFalse(hasattr(neutral, "optimal_product_id"))
        self.assertEqual(
            tuple(listing.product for listing in neutral.listings),
            tuple(listing.product for listing in cued.listings),
        )
        self.assertEqual(
            sum(listing.marketing_label is not None for listing in neutral.listings),
            0,
        )
        self.assertEqual(
            sum(listing.marketing_label is not None for listing in cued.listings),
            5,
        )


if __name__ == "__main__":
    unittest.main()
