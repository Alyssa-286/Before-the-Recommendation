"""Tests for stable trial IDs, separated trace data, and failure preservation."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from before_recommendation.failures import (
    FAILURE_TAXONOMY_VERSION,
    FailureCategory,
    FailureEvent,
    JsonlFailureLogger,
    category_for_parse_status,
    classify_exception,
)
from before_recommendation.output_parser import ParseStatus, parse_output
from before_recommendation.tracing import (
    AgentVisibleInput,
    JsonlTraceLogger,
    OutputAttemptTrace,
    TRACE_SCHEMA_VERSION,
    TraceEvent,
    TrialIdentity,
    TrialTrace,
)


def identity(**changes: object) -> TrialIdentity:
    data = {
        "scenario_id": "scenario-0001",
        "profile_id": "objective-0001",
        "goal_condition": "ambiguous",
        "marketing_condition": "neutral",
        "model_family": "deterministic_mock",
        "model_version": "mock-1",
        "repetition": 1,
        "prompt_template_id": "ambiguous-v1",
        "experiment_version": "phase1-deterministic-0.1.0",
        "config_sha256": "a" * 64,
        "random_seed": 20260930,
        "code_revision": "abcdef0",
    }
    data.update(changes)
    return TrialIdentity(**data)


def output_json() -> str:
    return json.dumps({
        "catalog_inspected": True,
        "clarification_needed": False,
        "clarification_question": None,
        "question_target": None,
        "simulated_user_answer": None,
        "preference_weights": {"price": 0.4, "quality": 0.3, "durability": 0.2, "sustainability": 0.1},
        "ranked_products": ["LumaBook_P01"],
        "evidence_used": ["price"],
        "uncertainty": 0.2,
        "final_explanation": "The recommendation balances a ₹40,000 budget and quality.",
    }, ensure_ascii=False)


def trial_trace(trial_identity: TrialIdentity | None = None) -> TrialTrace:
    raw = output_json()
    parsed = parse_output(raw, ("LumaBook_P01",))
    return TrialTrace(
        identity=trial_identity or identity(),
        started_at_utc="2026-09-30T14:00:00Z",
        completed_at_utc="2026-09-30T14:00:02Z",
        agent_visible_input=AgentVisibleInput(
            "I need a laptop for college.",
            ({"product_id": "LumaBook_P01", "price_inr": 40000, "marketing_label": None},),
        ),
        events=(
            TraceEvent(0, "environment", "trial_started", {"request_template": "ambiguous-v1"}),
            TraceEvent(1, "agent", "catalog_inspected", {"product_count": 1}),
        ),
        attempts=(OutputAttemptTrace(1, parsed),),
        derived_metrics={"regret": 0.0, "representation_error": 0.1},
        evaluator_private={
            "controlled_objective": {"price": 0.4, "quality": 0.3, "durability": 0.2, "sustainability": 0.1},
            "optimal_product_id": "LumaBook_P01",
        },
    )


class TracingTests(unittest.TestCase):
    def test_trial_id_is_stable_and_covers_condition_and_configuration(self) -> None:
        base = identity()
        self.assertEqual(base.trial_id, identity().trial_id)
        self.assertNotEqual(base.trial_id, identity(marketing_condition="scarcity").trial_id)
        self.assertNotEqual(base.trial_id, identity(config_sha256="b" * 64).trial_id)
        self.assertNotEqual(base.trial_id, identity(code_revision="1234567").trial_id)
        self.assertEqual(len(base.trial_id), 64)

    def test_trace_format_separates_agent_visible_raw_derived_and_hidden_evaluator_data(self) -> None:
        record = trial_trace().as_dict()
        self.assertEqual(TRACE_SCHEMA_VERSION, record["trace_schema_version"])
        self.assertEqual(record["agent_visible"]["request_text"], "I need a laptop for college.")
        self.assertEqual(len(record["agent_visible"]["prompt_sha256"]), 64)
        self.assertEqual(record["identity"]["code_revision"], "abcdef0")
        self.assertEqual(record["raw"]["attempts"][0]["raw_response"], output_json())
        self.assertEqual(record["derived"]["attempts"][0]["parse_status"], "valid")
        self.assertIn("controlled_objective", record["evaluator_private"])
        self.assertNotIn("controlled_objective", record["agent_visible"])

    def test_trace_schema_declares_versioned_required_separation(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "trace.v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["x-schema-version"], TRACE_SCHEMA_VERSION)
        self.assertIn("evaluator_private", schema["required"])
        self.assertIn("raw", schema["required"])
        self.assertIn("derived", schema["required"])

    def test_jsonl_append_and_reload_preserve_raw_output_and_unicode_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "traces.jsonl"
            logger = JsonlTraceLogger(path)
            logger.append(trial_trace())
            rows = logger.read_all()
            self.assertEqual(len(rows), 1)
            raw = rows[0]["raw"]["attempts"][0]["raw_response"]
            self.assertEqual(raw, output_json())
            self.assertIn("₹40,000", path.read_text(encoding="utf-8"))
            self.assertEqual(path.read_bytes().count(b"\n"), 1)

    def test_invalid_output_and_recovery_attempt_are_both_preserved(self) -> None:
        first_raw = "{broken"
        second_raw = output_json()
        trace = replace(
            trial_trace(),
            attempts=(
                OutputAttemptTrace(1, parse_output(first_raw, ("LumaBook_P01",))),
                OutputAttemptTrace(2, parse_output(second_raw, ("LumaBook_P01",))),
            ),
            failures=(FailureEvent(FailureCategory.INVALID_JSON, "parse", "Initial JSON parse failed.", True, 1),),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "traces.jsonl"
            JsonlTraceLogger(path).append(trace)
            row = JsonlTraceLogger(path).read_all()[0]
            self.assertEqual([item["raw_response"] for item in row["raw"]["attempts"]], [first_raw, second_raw])
            self.assertEqual([item["parse_status"] for item in row["derived"]["attempts"]], ["invalid_json", "valid"])
            self.assertEqual(row["failures"][0]["category"], "invalid_json")

    def test_duplicate_trial_trace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            logger = JsonlTraceLogger(Path(temporary) / "traces.jsonl")
            logger.append(trial_trace())
            with self.assertRaisesRegex(ValueError, "already exists"):
                logger.append(trial_trace())

    def test_corrupt_history_is_raised_instead_of_silently_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "traces.jsonl"
            path.write_bytes(b'{"valid":true}\nnot-json\n')
            with self.assertRaisesRegex(ValueError, "Invalid JSONL record"):
                JsonlTraceLogger(path)

    def test_failure_taxonomy_maps_parser_and_transport_errors(self) -> None:
        self.assertEqual(FAILURE_TAXONOMY_VERSION, "1.0.0")
        self.assertEqual(category_for_parse_status(ParseStatus.VALID), None)
        self.assertEqual(category_for_parse_status(ParseStatus.INVALID_JSON), FailureCategory.INVALID_JSON)
        self.assertEqual(classify_exception(TimeoutError()), FailureCategory.TIMEOUT)
        self.assertEqual(classify_exception(RuntimeError(), retry=True), FailureCategory.RETRY_EXECUTION_FAILURE)

    def test_failure_logger_appends_distinct_taxonomy_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            logger = JsonlFailureLogger(Path(temporary) / "failures.jsonl")
            logger.record("trial-a", FailureEvent(FailureCategory.TIMEOUT, "agent_call", "Call timed out.", True, 1))
            logger.record("trial-a", FailureEvent(FailureCategory.INVALID_JSON, "parse", "Could not parse response.", True, 1))
            rows = logger.read_all()
            self.assertEqual(len(rows), 2)
            self.assertEqual([row["failure"]["category"] for row in rows], ["timeout", "invalid_json"])
            self.assertTrue(all(row["trial_id"] == "trial-a" for row in rows))


if __name__ == "__main__":
    unittest.main()
