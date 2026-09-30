"""Tests for the non-inferential Phase 1 analysis skeleton."""

import json
import unittest

from before_recommendation.analysis import build_trial_rows, summarize_trial_rows
from before_recommendation.failures import FailureCategory, FailureEvent
from before_recommendation.output_parser import parse_output
from before_recommendation.tracing import (
    AgentVisibleInput,
    OutputAttemptTrace,
    TraceEvent,
    TrialIdentity,
    TrialTrace,
)


def trial_trace(
    trial_id_part: str,
    goal: str,
    marketing: str,
    *,
    clarify: bool,
    valid: bool = True,
) -> dict[str, object]:
    identity = TrialIdentity(
        scenario_id=f"scenario-{trial_id_part}",
        profile_id=f"objective-{trial_id_part}",
        goal_condition=goal,
        marketing_condition=marketing,
        model_family="deterministic_mock",
        model_version="mock-1",
        repetition=1,
        prompt_template_id=f"{goal}-v1-01",
        experiment_version="phase1-deterministic-0.1.0",
        config_sha256="a" * 64,
        random_seed=20260930,
        code_revision="abcdef0",
    )
    if valid:
        output = {
            "catalog_inspected": True,
            "clarification_needed": clarify,
            "clarification_question": "What matters most?" if clarify else None,
            "question_target": "price" if clarify else None,
            "simulated_user_answer": "Price matters most." if clarify else None,
            "preference_weights": {"price": 0.4, "quality": 0.3, "durability": 0.2, "sustainability": 0.1},
            "ranked_products": ["LumaBook_P01"],
            "evidence_used": ["price"],
            "uncertainty": 0.2,
            "final_explanation": "A validated mock response.",
        }
        attempt = OutputAttemptTrace(1, parse_output(json.dumps(output), ("LumaBook_P01",)))
        terminal_type = "trial_completed"
        metrics = {
            "preference_representation_error": 0.1,
            "top_recommended_product_id": "LumaBook_P01",
            "recommended_utility": 0.8,
            "regret": 0.05,
            "constraint_violated": False,
        }
        failure_items = ()
    else:
        attempt = OutputAttemptTrace(1, parse_output("{bad", ("LumaBook_P01",)))
        terminal_type = "trial_failed"
        metrics = {}
        failure_items = (FailureEvent(FailureCategory.INVALID_JSON, "parse", "Invalid JSON.", False, 1),)
    trace = TrialTrace(
        identity=identity,
        started_at_utc="2026-09-30T14:00:00Z",
        completed_at_utc="2026-09-30T14:00:01Z",
        agent_visible_input=AgentVisibleInput("A laptop request.", ({"product_id": "LumaBook_P01"},)),
        events=(TraceEvent(0, "harness", terminal_type, {}),),
        attempts=(attempt,),
        derived_metrics=metrics,
        evaluator_private={"objective_id": identity.profile_id},
        failures=failure_items,
    )
    return trace.as_dict()


class AnalysisTests(unittest.TestCase):
    def test_builds_one_tidy_row_per_trial_and_summarizes_primary_descriptives(self) -> None:
        traces = (
            trial_trace("1", "ambiguous", "neutral", clarify=True),
            trial_trace("2", "explicit", "discount", clarify=False),
            trial_trace("3", "ambiguous", "scarcity", clarify=False, valid=False),
        )
        rows = build_trial_rows(traces)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["code_revision"], "abcdef0")
        summary = summarize_trial_rows(rows)
        self.assertEqual(summary["trial_count"], 3)
        self.assertEqual(summary["valid_trial_count"], 2)
        self.assertEqual(summary["failed_trial_count"], 1)
        self.assertEqual(summary["clarification_rate"], 0.5)
        self.assertAlmostEqual(summary["mean_regret"], 0.05)
        self.assertEqual(summary["failure_event_counts"], {"invalid_json": 1})
        self.assertFalse(summary["inferential_statistics_run"])

    def test_duplicate_trial_ids_are_rejected(self) -> None:
        one = trial_trace("same", "ambiguous", "neutral", clarify=True)
        with self.assertRaisesRegex(ValueError, "Duplicate trial_id"):
            build_trial_rows((one, one))

    def test_empty_summary_has_null_means_and_zero_counts(self) -> None:
        summary = summarize_trial_rows(())
        self.assertEqual(summary["trial_count"], 0)
        self.assertEqual(summary["valid_trial_count"], 0)
        self.assertIsNone(summary["clarification_rate"])
        self.assertIsNone(summary["mean_regret"])


if __name__ == "__main__":
    unittest.main()
