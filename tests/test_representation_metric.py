"""Tests for the pre-specified half-L1 preference-representation metric."""

import unittest

from before_recommendation.config import load_phase1_config
from before_recommendation.evaluator import preference_representation_error
from before_recommendation.objectives import generate_objectives


class RepresentationMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.objective = generate_objectives(load_phase1_config(), count=1)[0]

    def test_exact_controlled_weights_have_zero_error(self) -> None:
        self.assertEqual(preference_representation_error(self.objective, self.objective.as_dict()), 0.0)

    def test_half_l1_matches_locked_definition(self) -> None:
        truth = self.objective.as_dict()
        alternative = {"price": 0.1, "quality": 0.2, "durability": 0.3, "sustainability": 0.4}
        expected = 0.5 * sum(abs(alternative[key] - truth[key]) for key in truth)
        self.assertAlmostEqual(preference_representation_error(self.objective, alternative), expected)

    def test_rejects_missing_extra_nonfinite_out_of_range_and_nonunit_weights(self) -> None:
        base = self.objective.as_dict()
        invalid = []
        invalid.append({key: value for key, value in base.items() if key != "price"})
        invalid.append({**base, "repairability": 0.1})
        invalid.append({**base, "price": float("inf")})
        invalid.append({**base, "price": 10**400})
        invalid.append({**base, "price": -0.1})
        invalid.append({**base, "price": base["price"] + 0.01})
        for weights in invalid:
            with self.subTest(weights=weights):
                with self.assertRaises(ValueError):
                    preference_representation_error(self.objective, weights)


if __name__ == "__main__":
    unittest.main()
