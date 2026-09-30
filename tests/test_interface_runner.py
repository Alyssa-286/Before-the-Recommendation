"""Deterministic interface pilot tests; no live model adapter is present."""

import json
from pathlib import Path
import tempfile
import unittest

from before_recommendation.checkpoint import CheckpointStore, TrialStatus
from before_recommendation.conditions import MarketingCondition
from before_recommendation.failures import FailureCategory, JsonlFailureLogger
from before_recommendation.interface_runner import run_mock_interface_trial
from before_recommendation.mock_agent import DeterministicMockAgent, MockAgentConfig
from before_recommendation.output_parser import parse_output
from before_recommendation.prompts import GoalCondition
from before_recommendation.scenarios import generate_scenarios
from before_recommendation.tracing import JsonlTraceLogger


class InterfaceRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = generate_scenarios()[0]

    def run_case(self, temporary: str, *, goal: GoalCondition, marketing: MarketingCondition, config: MockAgentConfig):
        root = Path(temporary)
        checkpoint = CheckpointStore(root / "checkpoint.sqlite3", self.scenario.config.config_sha256)
        trace_logger = JsonlTraceLogger(root / "traces.jsonl")
        failure_logger = JsonlFailureLogger(root / "failures.jsonl")
        agent = DeterministicMockAgent(config)
        result = run_mock_interface_trial(
            self.scenario,
            goal_condition=goal,
            marketing_condition=marketing,
            agent=agent,
            checkpoint=checkpoint,
            trace_logger=trace_logger,
            failure_logger=failure_logger,
            model_version="mock-1.0.0",
        )
        return result, agent, checkpoint, trace_logger, failure_logger

    def test_clarification_trial_runs_sim_user_parse_score_trace_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, agent, checkpoint, trace_logger, failure_logger = self.run_case(
                temporary,
                goal=GoalCondition.AMBIGUOUS,
                marketing=MarketingCondition.SOCIAL_PROOF,
                config=MockAgentConfig(clarification_needed=True, question_target="durability"),
            )
            self.assertIs(result.status, TrialStatus.COMPLETED)
            self.assertEqual(len(result.attempts), 1)
            self.assertTrue(result.attempts[0].valid)
            self.assertIn("matters", result.simulated_user_answer)
            self.assertGreaterEqual(result.metrics["preference_representation_error"], 0.0)
            self.assertGreaterEqual(result.metrics["regret"], 0.0)
            self.assertEqual(agent.recovery_count, 0)
            self.assertIs(checkpoint.get(result.trial_id).status, TrialStatus.COMPLETED)
            rows = trace_logger.read_all()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["agent_visible"]["request_text"], self.scenario.agent_view("ambiguous", "social_proof").user_request)
            self.assertTrue(any(listing["marketing_label"] for listing in row["agent_visible"]["catalog_listings"]))
            self.assertEqual(row["derived"]["metrics"]["top_recommended_product_id"], result.metrics["top_recommended_product_id"])
            self.assertNotIn("controlled_objective", row["agent_visible"])
            self.assertEqual(failure_logger.read_all(), ())
            event_types = [event["event_type"] for event in row["events"]]
            self.assertLess(event_types.index("catalog_inspection"), event_types.index("clarification_question"))
            self.assertLess(event_types.index("clarification_question"), event_types.index("clarification_answer"))
            self.assertLess(event_types.index("clarification_answer"), event_types.index("raw_response_received"))

    def test_explicit_no_clarification_trial_has_null_question_and_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, _, _, trace_logger, _ = self.run_case(
                temporary,
                goal=GoalCondition.EXPLICIT,
                marketing=MarketingCondition.NEUTRAL,
                config=MockAgentConfig(clarification_needed=False),
            )
            self.assertIs(result.status, TrialStatus.COMPLETED)
            self.assertIsNone(result.simulated_user_answer)
            output = result.attempts[0].data
            self.assertFalse(output["clarification_needed"])
            self.assertIsNone(output["clarification_question"])
            self.assertIsNone(output["question_target"])
            self.assertIsNone(output["simulated_user_answer"])
            self.assertNotIn("clarification_question", [event["event_type"] for event in trace_logger.read_all()[0]["events"]])

    def test_unsupported_target_gets_standard_uncertainty_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, _, _, _, _ = self.run_case(
                temporary,
                goal=GoalCondition.AMBIGUOUS,
                marketing=MarketingCondition.DISCOUNT,
                config=MockAgentConfig(clarification_needed=True, question_target="unsupported"),
            )
            self.assertIs(result.status, TrialStatus.COMPLETED)
            self.assertIn("haven't specified", result.simulated_user_answer)
            self.assertEqual(result.attempts[0].data["question_target"], "unsupported")

    def test_one_invalid_first_response_is_recovered_and_both_raw_attempts_are_logged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, agent, _, trace_logger, failure_logger = self.run_case(
                temporary,
                goal=GoalCondition.AMBIGUOUS,
                marketing=MarketingCondition.SCARCITY,
                config=MockAgentConfig(clarification_needed=True, emit_malformed_first_response=True),
            )
            self.assertIs(result.status, TrialStatus.COMPLETED)
            self.assertEqual(agent.recovery_count, 1)
            self.assertEqual([attempt.status.value for attempt in result.attempts], ["invalid_json", "valid"])
            row = trace_logger.read_all()[0]
            self.assertEqual(len(row["raw"]["attempts"]), 2)
            self.assertEqual(row["raw"]["attempts"][0]["raw_response"], "{deterministic mock malformed response")
            self.assertEqual(row["raw"]["attempts"][1]["raw_response"], result.attempts[1].raw_output)
            logged = failure_logger.read_all()
            self.assertEqual(len(logged), 1)
            self.assertEqual(logged[0]["failure"]["category"], FailureCategory.INVALID_JSON.value)
            self.assertTrue(logged[0]["failure"]["recoverable"])

    def test_clarification_before_inspection_is_a_preserved_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, _, checkpoint, trace_logger, failure_logger = self.run_case(
                temporary,
                goal=GoalCondition.AMBIGUOUS,
                marketing=MarketingCondition.NEUTRAL,
                config=MockAgentConfig(clarification_needed=True, inspect_catalog=False),
            )
            self.assertIs(result.status, TrialStatus.FAILED)
            self.assertIs(checkpoint.get(result.trial_id).status, TrialStatus.FAILED)
            categories = [row["failure"]["category"] for row in failure_logger.read_all()]
            self.assertEqual(categories, [
                FailureCategory.CATALOG_INSPECTION_MISSING.value,
                FailureCategory.CLARIFICATION_ORDER_VIOLATION.value,
            ])
            row = trace_logger.read_all()[0]
            self.assertEqual(row["raw"]["attempts"], [])
            self.assertEqual(row["derived"]["attempts"], [])

    def test_mock_only_run_does_not_expose_hidden_objective_to_agent(self) -> None:
        view = self.scenario.agent_view(GoalCondition.AMBIGUOUS, MarketingCondition.NEUTRAL)
        agent = DeterministicMockAgent(MockAgentConfig(clarification_needed=False))
        self.assertFalse(hasattr(view, "objective"))
        self.assertFalse(hasattr(agent, "objective"))
        start = agent.start_trial(view)
        self.assertTrue(start.catalog_inspected)
        raw = agent.final_response(view, None)
        self.assertTrue(parse_output(raw, [listing.product.product_id for listing in view.listings]).valid)


if __name__ == "__main__":
    unittest.main()
