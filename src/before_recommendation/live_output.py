"""Strict parser for the model-owned Phase 2 recommendation contract."""

from __future__ import annotations

import json
import math

from .output_parser import OutputParseResult, ParseStatus, ValidationIssue


LIVE_OUTPUT_SCHEMA_VERSION = "2.0.0"
WEIGHT_KEYS = ("price", "quality", "durability", "sustainability")
WEIGHT_SUM_TOLERANCE = 1e-6


class _DuplicateKeyError(ValueError):
    pass


def parse_live_output(raw_output: object, catalog_product_ids: tuple[str, ...]) -> OutputParseResult:
    """Validate tool arguments without coercion or silent repair; retain raw input."""
    if not isinstance(raw_output, str) or not raw_output.strip():
        return OutputParseResult(
            raw_output, None, ParseStatus.MALFORMED_RESPONSE,
            (ValidationIssue("$", "empty_or_non_text", "Response must be non-empty JSON text."),),
            LIVE_OUTPUT_SCHEMA_VERSION,
        )
    try:
        data = json.loads(
            raw_output,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, json.JSONDecodeError):
            message = f"Invalid JSON at line {exc.lineno}, column {exc.colno}."
        elif isinstance(exc, _DuplicateKeyError):
            message = "JSON object contains a duplicate key."
        else:
            message = "JSON contains a non-finite or invalid value."
        return OutputParseResult(
            raw_output, None, ParseStatus.INVALID_JSON,
            (ValidationIssue("$", "invalid_json", message),), LIVE_OUTPUT_SCHEMA_VERSION,
        )
    if not isinstance(data, dict):
        return OutputParseResult(
            raw_output, None, ParseStatus.MALFORMED_RESPONSE,
            (ValidationIssue("$", "top_level_type", "Top-level JSON value must be an object."),),
            LIVE_OUTPUT_SCHEMA_VERSION,
        )
    errors: list[ValidationIssue] = []
    required = {"preference_weights", "ranked_products", "evidence_used", "uncertainty", "final_explanation"}
    for name in sorted(required - data.keys()):
        errors.append(ValidationIssue(f"$.{name}", "required", "Required field is missing."))
    for name in sorted(data.keys() - required):
        errors.append(ValidationIssue(f"$.{name}", "additional_property", "Field is not defined by schema version 2."))
    if required - data.keys():
        return OutputParseResult(raw_output, data, ParseStatus.SCHEMA_VALIDATION_FAILURE, tuple(errors), LIVE_OUTPUT_SCHEMA_VERSION)

    weights = data["preference_weights"]
    if not isinstance(weights, dict):
        errors.append(ValidationIssue("$.preference_weights", "type", "Preference weights must be an object."))
    else:
        for name in sorted(set(WEIGHT_KEYS) - weights.keys()):
            errors.append(ValidationIssue(f"$.preference_weights.{name}", "required", "Weight is required."))
        for name in sorted(weights.keys() - set(WEIGHT_KEYS)):
            errors.append(ValidationIssue(f"$.preference_weights.{name}", "additional_property", "Weight is not a locked objective dimension."))
        numeric: list[float] = []
        for name in WEIGHT_KEYS:
            if name not in weights:
                continue
            value = weights[name]
            if not _finite_number(value):
                errors.append(ValidationIssue(f"$.preference_weights.{name}", "type", "Weight must be a finite number."))
            else:
                numeric.append(float(value))
                if not 0 <= value <= 1:
                    errors.append(ValidationIssue(f"$.preference_weights.{name}", "bounds", "Weight must be within [0, 1]."))
        if len(numeric) == len(WEIGHT_KEYS) and abs(sum(numeric) - 1.0) > WEIGHT_SUM_TOLERANCE:
            errors.append(ValidationIssue("$.preference_weights", "sum", f"Weights must sum to 1 within {WEIGHT_SUM_TOLERANCE:g}."))

    ranking = data["ranked_products"]
    if not isinstance(ranking, list) or not ranking:
        errors.append(ValidationIssue("$.ranked_products", "type_or_empty", "Ranking must be a non-empty array."))
    else:
        seen: set[str] = set()
        catalog_ids = frozenset(catalog_product_ids)
        for index, product_id in enumerate(ranking):
            path = f"$.ranked_products[{index}]"
            if not _nonempty_text(product_id):
                errors.append(ValidationIssue(path, "type", "Product IDs must be non-empty strings."))
            elif product_id in seen:
                errors.append(ValidationIssue(path, "duplicate", "Product IDs must not repeat."))
            elif product_id not in catalog_ids:
                errors.append(ValidationIssue(path, "unknown_product", "Product ID is not present in this trial catalog."))
            if isinstance(product_id, str):
                seen.add(product_id)

    evidence = data["evidence_used"]
    if not isinstance(evidence, list):
        errors.append(ValidationIssue("$.evidence_used", "type", "Evidence fields must be an array."))
    else:
        seen_evidence: set[str] = set()
        for index, item in enumerate(evidence):
            path = f"$.evidence_used[{index}]"
            if not _nonempty_text(item):
                errors.append(ValidationIssue(path, "type_or_empty", "Evidence must contain non-empty text."))
            elif item in seen_evidence:
                errors.append(ValidationIssue(path, "duplicate", "Evidence values must be unique."))
            if isinstance(item, str):
                seen_evidence.add(item)

    uncertainty = data["uncertainty"]
    if not _finite_number(uncertainty):
        errors.append(ValidationIssue("$.uncertainty", "type", "Uncertainty must be a finite number."))
    elif not 0 <= uncertainty <= 1:
        errors.append(ValidationIssue("$.uncertainty", "bounds", "Uncertainty must be within [0, 1]."))
    if not _nonempty_text(data["final_explanation"]):
        errors.append(ValidationIssue("$.final_explanation", "type_or_empty", "Final explanation must be non-empty text."))
    return OutputParseResult(
        raw_output, data, ParseStatus.VALID if not errors else ParseStatus.SCHEMA_VALIDATION_FAILURE,
        tuple(errors), LIVE_OUTPUT_SCHEMA_VERSION,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False
