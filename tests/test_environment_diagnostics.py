from __future__ import annotations

import unittest

from before_recommendation.catalog import catalog_fingerprint, generate_catalog
from before_recommendation.conditions import generate_cue_arms
from before_recommendation.config import load_phase1_config
from before_recommendation.environment_diagnostics import evaluate_environment
from before_recommendation.experiment_config import CORE_CONFIG_PATH
from before_recommendation.objectives import generate_objectives


class EnvironmentDiagnosticsTests(unittest.TestCase):
    def test_phase1_catalog_fails_documented_dominance_checks(self) -> None:
        config = load_phase1_config()
        report = evaluate_environment(generate_catalog(config), generate_objectives(config), config)
        self.assertFalse(report.passed)
        self.assertEqual(report.checks["distinct_optimal_products"]["value"], 1)

    def test_core_v2_catalog_passes_every_prespecified_check(self) -> None:
        config = load_phase1_config(CORE_CONFIG_PATH)
        report = evaluate_environment(generate_catalog(config), generate_objectives(config), config)
        failing = [name for name, check in report.checks.items() if not check["pass"]]
        self.assertEqual(failing, [])
        self.assertGreaterEqual(len(report.optimal_counts), 5)

    def test_core_v2_preserves_objectives_cue_seed_and_generator(self) -> None:
        old, new = load_phase1_config(), load_phase1_config(CORE_CONFIG_PATH)
        self.assertEqual([o.weights for o in generate_objectives(old)], [o.weights for o in generate_objectives(new)])
        self.assertEqual(old.cues_seed, new.cues_seed)
        self.assertEqual(old.catalog_count, new.catalog_count)
        self.assertNotEqual(old.catalog_seed, new.catalog_seed)

    def test_core_v2_reproduces_exactly_and_cues_never_touch_facts(self) -> None:
        config = load_phase1_config(CORE_CONFIG_PATH)
        catalog = generate_catalog(config)
        self.assertEqual(catalog_fingerprint(catalog), catalog_fingerprint(generate_catalog(config)))
        base = {p.product_id: p for p in catalog.products}
        for arm in generate_cue_arms(catalog, config):
            for listing in arm.listings:
                self.assertEqual(listing.product, base[listing.product.product_id])


if __name__ == "__main__":
    unittest.main()
