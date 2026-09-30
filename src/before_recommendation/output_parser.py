"""Strict, versioned parser for observable research-trial outputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import math
from pathlib import Path
from typing import Callable, Iterable


OUTPUT_SCHEMA_VERSION = "1.0.0"
WEIGHT_SUM_TOLERANCE = 1e-6
WEIGHT_KEYS = ("price", "quality", "durability", "sustainability")
SUPPORTED_QUESTION_TARGETS = frozenset((*WEIGHT_KEYS, "unsupported"))
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "agent_output.v1.schema.json"


class ParseStatus(StrEnum):
    VALID = "valid"
    INVALID_JSON = "invalid_json"
    SCHEMA_VALIDATION_FAILURE = "schema_validation_failure"
    MALFORMED_RESPONSE = "malformed_response"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class OutputParseResult:
    raw_output: object
    data: dict[str, object] | None
    status: ParseStatus
    errors: tuple[ValidationIssue, ...]
    schema_version: str = OUTPUT_SCHEMA_VERSION

    @property
    def valid(self) -> bool:
        return self.status is ParseStatus.VALID


@dataclass(frozen=True, slots=True)
class ParseRun:
    attempts: tuple[OutputParseResult, ...]
    retry_execution_error: str | None = None

    @property
    def final(self) -> OutputParseResult:
        return self.attempts[-1]

    @property
    def retried(self) -> bool:
        return len(self.attempts) > 1 or self.retry_execution_error is not None


class _DuplicateKeyError(ValueError):
    pass


def load_output_schema(path: str | Path = DEFAULT_SCHEMA_PATH) -> dict[str, object]:
    """Load the checked-in JSON Schema so callers can record its versioned contract."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("title") != "Before the Recommendation observable agent output":
        raise ValueError("Unexpected output schema document.")
    return payload


def parse_output(raw_output: object, catalog_product_ids: Iterable[str]) -> OutputParseResult:
    """Parse without coercion; retain the exact input object on every outcome."""
    if not isinstance(raw_output, str) or not raw_output.strip():
        return OutputParseResult(
            raw_output,
            None,
            ParseStatus.MALFORMED_RESPONSE,
            (ValidationIssue("$", "empty_or_non_text", "Response must be non-empty text."),),
        )
    try:
        data = json.loads(
            raw_output,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"Non-finite number {token}")),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        return OutputParseResult(
            raw_output,
            None,
            ParseStatus.INVALID_JSON,
            (ValidationIssue("$", "invalid_json", _safe_parse_message(exc)),),
        )

    if not isinstance(data, dict):
        return OutputParseResult(
            raw_output,
            None,
            ParseStatus.MALFORMED_RESPONSE,
            (ValidationIssue("$", "top_level_type", "Top-level JSON value must be an object."),),
        )

    errors = _validate_payload(data, frozenset(catalog_product_ids))
    return OutputParseResult(
        raw_output,
        data,
        ParseStatus.VALID if not errors else ParseStatus.SCHEMA_VALIDATION_FAILURE,
        tuple(errors),
    )


def parse_with_one_retry(
    first_raw_output: object,
    catalog_product_ids: Iterable[str],
    retry_provider: Callable[[OutputParseResult], object],
) -> ParseRun:
    """Request at most one replacement after JSON/schema validation failure.

    The initial and replacement raw values are both retained verbatim. Blank,
    non-text, and top-level non-object responses are not auto-retried.
    """
    ids = tuple(catalog_product_ids)
    first = parse_output(first_raw_output, ids)
    retryable = first.status in {ParseStatus.INVALID_JSON, ParseStatus.SCHEMA_VALIDATION_FAILURE} or (
        first.status is ParseStatus.MALFORMED_RESPONSE
        and any(error.code == "top_level_type" for error in first.errors)
    )
    if first.valid or not retryable:
        return ParseRun((first,))
    try:
        retry_raw = retry_provider(first)
    except Exception as exc:  # The exception type is retained, not its potentially sensitive message.
        return ParseRun((first,), retry_execution_error=type(exc).__name__)
    second = parse_output(retry_raw, ids)
    return ParseRun((first, second))


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"Duplicate object key: {key}")
        result[key] = value
    return result


def _safe_parse_message(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return f"Invalid JSON at line {exc.lineno}, column {exc.colno}."
    if isinstance(exc, _DuplicateKeyError):
        return "JSON object contains a duplicate key."
    return "JSON contains a non-finite or invalid value."


def _validate_payload(data: dict[str, object], catalog_ids: frozenset[str]) -> list[ValidationIssue]:
    errors: list[ValidationIssue] = []

    def issue(path: str, code: str, message: str) -> None:
        errors.append(ValidationIssue(path, code, message))

    required = {
        "catalog_inspected", "clarification_needed", "clarification_question", "question_target",
        "simulated_user_answer", "preference_weights", "ranked_products", "evidence_used",
        "uncertainty", "final_explanation",
    }
    missing = sorted(required - data.keys())
    for key in missing:
        issue(f"$.{key}", "required", "Required field is missing.")
    for key in sorted(data.keys() - required):
        issue(f"$.{key}", "additional_property", "Field is not defined by schema version 1.")
    if missing:
        return errors

    for key in ("catalog_inspected", "clarification_needed"):
        if type(data[key]) is not bool:
            issue(f"$.{key}", "type", "Value must be a boolean.")

    clarifies = data["clarification_needed"]
    question = data["clarification_question"]
    target = data["question_target"]
    answer = data["simulated_user_answer"]
    if type(clarifies) is bool:
        if clarifies:
            if not _nonempty_text(question):
                issue("$.clarification_question", "clarification_required", "A clarification requires non-empty question text.")
            if not isinstance(target, str) or target not in SUPPORTED_QUESTION_TARGETS:
                issue("$.question_target", "unsupported_target", "Target must be a supported dimension or 'unsupported'.")
            if not _nonempty_text(answer):
                issue("$.simulated_user_answer", "clarification_required", "A clarification requires its simulated-user answer.")
        elif question is not None or target is not None or answer is not None:
            issue("$.clarification_question", "unexpected_clarification_fields", "Question, target, and answer must be null when clarification is false.")

    weights = data["preference_weights"]
    if not isinstance(weights, dict):
        issue("$.preference_weights", "type", "Preference weights must be an object.")
    else:
        absent = sorted(set(WEIGHT_KEYS) - weights.keys())
        extra = sorted(weights.keys() - set(WEIGHT_KEYS))
        for key in absent:
            issue(f"$.preference_weights.{key}", "required", "Weight is required.")
        for key in extra:
            issue(f"$.preference_weights.{key}", "additional_property", "Weight is not a locked objective dimension.")
        numeric: list[float] = []
        for key in WEIGHT_KEYS:
            if key not in weights:
                continue
            value = weights[key]
            if not _is_finite_number(value):
                issue(f"$.preference_weights.{key}", "type", "Weight must be a finite number.")
                continue
            numeric.append(float(value))
            if not 0 <= value <= 1:
                issue(f"$.preference_weights.{key}", "bounds", "Weight must be between 0 and 1 inclusive.")
        if len(numeric) == len(WEIGHT_KEYS) and abs(sum(numeric) - 1.0) > WEIGHT_SUM_TOLERANCE:
            issue("$.preference_weights", "sum", f"Weights must sum to 1 within {WEIGHT_SUM_TOLERANCE:g}.")

    ranking = data["ranked_products"]
    if not isinstance(ranking, list) or not ranking:
        issue("$.ranked_products", "type_or_empty", "Ranking must be a non-empty array.")
    else:
        seen: set[str] = set()
        for index, product_id in enumerate(ranking):
            if not _nonempty_text(product_id):
                issue(f"$.ranked_products[{index}]", "type", "Product IDs must be non-empty strings.")
            elif product_id in seen:
                issue(f"$.ranked_products[{index}]", "duplicate", "Product IDs must not repeat.")
            elif product_id not in catalog_ids:
                issue(f"$.ranked_products[{index}]", "unknown_product", "Product ID is not present in this trial catalog.")
            seen.add(product_id) if isinstance(product_id, str) else None

    evidence = data["evidence_used"]
    if not isinstance(evidence, list):
        issue("$.evidence_used", "type", "Evidence fields must be an array.")
    else:
        _validate_string_array(evidence, "$.evidence_used", issue, unique=True)

    uncertainty = data["uncertainty"]
    if not _is_finite_number(uncertainty):
        issue("$.uncertainty", "type", "Uncertainty must be a finite number.")
    elif not 0 <= uncertainty <= 1:
        issue("$.uncertainty", "bounds", "Uncertainty must be between 0 and 1 inclusive.")

    if not _nonempty_text(data["final_explanation"]):
        issue("$.final_explanation", "type_or_empty", "Final explanation must be non-empty text.")
    return errors


def _validate_string_array(values: list[object], path: str, issue: Callable[[str, str, str], None], unique: bool) -> None:
    seen: set[str] = set()
    for index, value in enumerate(values):
        if not _nonempty_text(value):
            issue(f"{path}[{index}]", "type_or_empty", "Value must be non-empty text.")
            continue
        if unique and value in seen:
            issue(f"{path}[{index}]", "duplicate", "Values must be unique.")
        seen.add(value)


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_finite_number(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False
