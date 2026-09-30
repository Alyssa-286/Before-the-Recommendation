"""Contract tests for the versioned observable-output parser."""

import json
from pathlib import Path
import unittest

from before_recommendation.output_parser import (
    OUTPUT_SCHEMA_VERSION,
    ParseStatus,
    load_output_schema,
    parse_output,
    parse_with_one_retry,
)


CATALOG_IDS = ("LumaBook_P01", "LumaBook_P02", "LumaBook_P03")


def payload() -> dict[str, object]:
    return {
        "catalog_inspected": True,
        "clarification_needed": True,
        "clarification_question": "What matters most: price or durability?",
        "question_target": "price",
        "simulated_user_answer": "Price matters most to me.",
        "preference_weights": {
            "price": 0.4,
            "quality": 0.3,
            "durability": 0.2,
            "sustainability": 0.1,
        },
        "ranked_products": ["LumaBook_P02", "LumaBook_P01"],
        "evidence_used": ["price", "durability"],
        "uncertainty": 0.25,
        "final_explanation": "This ranking prioritizes the stated budget and durability.",
    }


def serialized(value: object | None = None) -> str:
    return json.dumps(payload() if value is None else value, separators=(",", ":"))


class OutputParserTests(unittest.TestCase):
    def test_schema_is_checked_in_and_versioned(self) -> None:
        schema = load_output_schema()
        self.assertEqual(OUTPUT_SCHEMA_VERSION, "1.0.0")
        self.assertEqual(schema["x-schema-version"], OUTPUT_SCHEMA_VERSION)
        self.assertIn("clarification_needed", schema["required"])
        self.assertTrue(Path(__file__).resolve().parents[1].joinpath("schemas/agent_output.v1.schema.json").is_file())

    def test_accepts_valid_clarification_and_no_clarification_payloads(self) -> None:
        raw = serialized()
        result = parse_output(raw, CATALOG_IDS)
        self.assertTrue(result.valid)
        self.assertIs(result.status, ParseStatus.VALID)
        self.assertEqual(result.raw_output, raw)
        self.assertEqual(result.data, payload())

        no_clarification = payload()
        no_clarification.update(
            clarification_needed=False,
            clarification_question=None,
            question_target=None,
            simulated_user_answer=None,
        )
        self.assertTrue(parse_output(serialized(no_clarification), CATALOG_IDS).valid)

    def test_invalid_json_duplicate_keys_and_nonfinite_values_are_rejected(self) -> None:
        invalid = parse_output("{not json", CATALOG_IDS)
        self.assertIs(invalid.status, ParseStatus.INVALID_JSON)
        self.assertEqual(invalid.raw_output, "{not json")

        duplicate = '{"catalog_inspected":true,"catalog_inspected":false}'
        self.assertIs(parse_output(duplicate, CATALOG_IDS).status, ParseStatus.INVALID_JSON)
        self.assertIs(parse_output(serialized().replace('"uncertainty":0.25', '"uncertainty":NaN'), CATALOG_IDS).status, ParseStatus.INVALID_JSON)

    def test_malformed_response_does_not_coerce_or_retry(self) -> None:
        for raw in (None, 3, "", "   ", "[]"):
            with self.subTest(raw=raw):
                result = parse_output(raw, CATALOG_IDS)
                self.assertIs(result.status, ParseStatus.MALFORMED_RESPONSE)
                self.assertIs(result.raw_output, raw)
        calls: list[object] = []
        outcome = parse_with_one_retry("", CATALOG_IDS, lambda previous: calls.append(previous))
        self.assertEqual(len(outcome.attempts), 1)
        self.assertEqual(calls, [])

    def test_schema_validation_covers_required_types_bounds_and_extra_fields(self) -> None:
        cases = []
        missing = payload()
        del missing["catalog_inspected"]
        cases.append(missing)
        wrong_boolean = payload()
        wrong_boolean["catalog_inspected"] = 1
        cases.append(wrong_boolean)
        out_of_range = payload()
        out_of_range["uncertainty"] = 1.01
        cases.append(out_of_range)
        extra = payload()
        extra["private_reasoning"] = "should not be requested"
        cases.append(extra)
        for value in cases:
            with self.subTest(value=value):
                result = parse_output(serialized(value), CATALOG_IDS)
                self.assertIs(result.status, ParseStatus.SCHEMA_VALIDATION_FAILURE)
                self.assertTrue(result.errors)
                self.assertEqual(result.data, value)

    def test_weights_require_all_dimensions_finite_bounded_and_sum_to_one(self) -> None:
        for edit in (
            lambda p: p["preference_weights"].update(price=-0.1),
            lambda p: p["preference_weights"].update(price=1.1),
            lambda p: p["preference_weights"].update(price=0.2),
            lambda p: p["preference_weights"].update(price=10**400),
            lambda p: p["preference_weights"].pop("quality"),
            lambda p: p["preference_weights"].update(repairability=0.1),
        ):
            value = payload()
            edit(value)
            with self.subTest(weights=value["preference_weights"]):
                self.assertIs(parse_output(serialized(value), CATALOG_IDS).status, ParseStatus.SCHEMA_VALIDATION_FAILURE)

        near_sum = payload()
        near_sum["preference_weights"]["price"] += 5e-7
        self.assertTrue(parse_output(serialized(near_sum), CATALOG_IDS).valid)

    def test_question_fields_are_consistent_and_target_is_single_supported_dimension(self) -> None:
        for edit in (
            lambda p: p.update(clarification_question=""),
            lambda p: p.update(question_target="repairability"),
            lambda p: p.update(question_target=["price", "quality"]),
            lambda p: p.update(simulated_user_answer=None),
            lambda p: p.update(clarification_needed=False),
        ):
            value = payload()
            edit(value)
            with self.subTest(value=value):
                self.assertIs(parse_output(serialized(value), CATALOG_IDS).status, ParseStatus.SCHEMA_VALIDATION_FAILURE)

        unsupported = payload()
        unsupported["question_target"] = "unsupported"
        self.assertTrue(parse_output(serialized(unsupported), CATALOG_IDS).valid)

    def test_rankings_require_known_unique_nonempty_catalog_ids(self) -> None:
        for ranking in ([], ["LumaBook_P01", "LumaBook_P01"], ["Other_Laptop"], [""]):
            value = payload()
            value["ranked_products"] = ranking
            with self.subTest(ranking=ranking):
                self.assertIs(parse_output(serialized(value), CATALOG_IDS).status, ParseStatus.SCHEMA_VALIDATION_FAILURE)

    def test_retry_happens_at_most_once_only_for_json_or_schema_failure(self) -> None:
        corrected = serialized()
        calls = []
        outcome = parse_with_one_retry("broken", CATALOG_IDS, lambda first: calls.append(first) or corrected)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(outcome.attempts), 2)
        self.assertEqual(outcome.attempts[0].raw_output, "broken")
        self.assertEqual(outcome.final.raw_output, corrected)
        self.assertTrue(outcome.final.valid)

        invalid_schema = payload()
        invalid_schema["ranked_products"] = []
        calls.clear()
        outcome = parse_with_one_retry(serialized(invalid_schema), CATALOG_IDS, lambda first: calls.append(first) or corrected)
        self.assertEqual(len(calls), 1)
        self.assertTrue(outcome.final.valid)

        calls.clear()
        outcome = parse_with_one_retry(corrected, CATALOG_IDS, lambda first: calls.append(first) or corrected)
        self.assertEqual(len(calls), 0)
        self.assertEqual(len(outcome.attempts), 1)

    def test_retry_execution_error_preserves_original_failure_without_looping(self) -> None:
        calls = []

        def fail(_first):
            calls.append(True)
            raise TimeoutError("details are intentionally not copied into logs")

        outcome = parse_with_one_retry("bad", CATALOG_IDS, fail)
        self.assertEqual(len(calls), 1)
        self.assertEqual(outcome.retry_execution_error, "TimeoutError")
        self.assertEqual(len(outcome.attempts), 1)
        self.assertEqual(outcome.final.raw_output, "bad")

    def test_retry_is_exactly_once_for_top_level_json_shape_and_failed_recovery(self) -> None:
        corrected = serialized()
        calls = []
        result = parse_with_one_retry("[]", CATALOG_IDS, lambda first: calls.append(first) or corrected)
        self.assertEqual(len(calls), 1)
        self.assertEqual([attempt.raw_output for attempt in result.attempts], ["[]", corrected])
        self.assertTrue(result.final.valid)

        calls.clear()
        result = parse_with_one_retry("broken-first", CATALOG_IDS, lambda first: calls.append(first) or "broken-second")
        self.assertEqual(len(calls), 1)
        self.assertEqual([attempt.raw_output for attempt in result.attempts], ["broken-first", "broken-second"])
        self.assertIs(result.final.status, ParseStatus.INVALID_JSON)


if __name__ == "__main__":
    unittest.main()
