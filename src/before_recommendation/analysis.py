"""Descriptive analysis skeleton for validated trial-trace records.

This module only prepares trial-level rows and descriptive summaries. It does
not fit inferential models or treat mock runs as empirical evidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import Iterable


ANALYSIS_SCHEMA_VERSION = "2.0.0"


def build_trial_rows(records: Iterable[dict[str, object]]) -> tuple[dict[str, object], ...]:
    """Flatten versioned trace records into one deterministic row per trial."""
    rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for record in records:
        trial_id = record.get("trial_id")
        identity = record.get("identity")
        events = record.get("events")
        derived = record.get("derived")
        failures = record.get("failures")
        if not isinstance(trial_id, str) or not isinstance(identity, dict):
            raise ValueError("Trace record must contain a trial_id and identity object.")
        if trial_id in seen_ids:
            raise ValueError(f"Duplicate trial_id in analysis input: {trial_id}.")
        seen_ids.add(trial_id)
        if not isinstance(events, list) or not isinstance(derived, dict) or not isinstance(failures, list):
            raise ValueError(f"Trace {trial_id} is missing events, derived values, or failures.")
        attempts = derived.get("attempts")
        metrics = derived.get("metrics")
        if not isinstance(attempts, list) or not isinstance(metrics, dict):
            raise ValueError(f"Trace {trial_id} has an invalid derived section.")
        final_attempt = attempts[-1] if attempts else None
        final_status = final_attempt.get("parse_status") if isinstance(final_attempt, dict) else None
        output_schema_version = final_attempt.get("schema_version") if isinstance(final_attempt, dict) else None
        output = final_attempt.get("parsed_output") if isinstance(final_attempt, dict) else None
        if not isinstance(output, dict):
            output = {}
        last_event = events[-1] if events else {}
        terminal_type = last_event.get("event_type") if isinstance(last_event, dict) else None
        is_valid = terminal_type == "trial_completed" and final_status == "valid"
        failure_categories = tuple(
            str(item["category"])
            for item in failures
            if isinstance(item, dict) and isinstance(item.get("category"), str)
        )
        rows.append({
            "analysis_schema_version": ANALYSIS_SCHEMA_VERSION,
            "trial_id": trial_id,
            "scenario_id": identity.get("scenario_id"),
            "profile_id": identity.get("profile_id"),
            "goal_condition": identity.get("goal_condition"),
            "marketing_condition": identity.get("marketing_condition"),
            "model_family": identity.get("model_family"),
            "model_version": identity.get("model_version"),
            "repetition": identity.get("repetition"),
            "config_sha256": identity.get("config_sha256"),
            "code_revision": identity.get("code_revision"),
            "terminal_event": terminal_type,
            "is_valid": is_valid,
            "parse_status": final_status,
            "output_schema_version": output_schema_version,
            "clarification_needed": output.get("clarification_needed", metrics.get("clarification_needed")),
            "question_target": output.get("question_target", metrics.get("question_target")),
            "clarification_answer_supported": metrics.get("clarification_answer_supported"),
            "preference_weights": output.get("preference_weights"),
            "ranked_products": output.get("ranked_products"),
            "evidence_used": output.get("evidence_used"),
            "uncertainty": output.get("uncertainty"),
            "preference_representation_error": metrics.get("preference_representation_error"),
            "top_recommended_product_id": metrics.get("top_recommended_product_id"),
            "recommended_utility": metrics.get("recommended_utility"),
            "regret": metrics.get("regret"),
            "constraint_violated": metrics.get("constraint_violated"),
            "failure_categories": failure_categories,
        })
    return tuple(rows)


def summarize_trial_rows(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    """Produce only descriptive counts/means from already validated trial rows."""
    materialized = tuple(rows)
    valid = tuple(row for row in materialized if row.get("is_valid") is True)
    failure_counts: Counter[str] = Counter(
        category
        for row in materialized
        for category in row.get("failure_categories", ())
        if isinstance(category, str)
    )
    condition_groups: dict[tuple[object, object], list[dict[str, object]]] = defaultdict(list)
    for row in valid:
        condition_groups[(row.get("goal_condition"), row.get("marketing_condition"))].append(row)
    by_condition = []
    for (goal, marketing), group in sorted(condition_groups.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        by_condition.append({
            "goal_condition": goal,
            "marketing_condition": marketing,
            "valid_trial_count": len(group),
            "clarification_rate": _mean([float(row["clarification_needed"]) for row in group if type(row.get("clarification_needed")) is bool]),
            "mean_representation_error": _mean(_numeric(row.get("preference_representation_error")) for row in group),
            "mean_recommendation_utility": _mean(_numeric(row.get("recommended_utility")) for row in group),
            "mean_regret": _mean(_numeric(row.get("regret")) for row in group),
            "constraint_violation_count": sum(row.get("constraint_violated") is True for row in group),
        })
    valid_clarifications = [row["clarification_needed"] for row in valid if type(row.get("clarification_needed")) is bool]
    return {
        "analysis_schema_version": ANALYSIS_SCHEMA_VERSION,
        "trial_count": len(materialized),
        "valid_trial_count": len(valid),
        "failed_trial_count": len(materialized) - len(valid),
        "clarification_rate": _mean([float(value) for value in valid_clarifications]),
        "mean_representation_error": _mean(_numeric(row.get("preference_representation_error")) for row in valid),
        "mean_recommendation_utility": _mean(_numeric(row.get("recommended_utility")) for row in valid),
        "mean_regret": _mean(_numeric(row.get("regret")) for row in valid),
        "constraint_violation_count": sum(row.get("constraint_violated") is True for row in valid),
        "failure_event_counts": dict(sorted(failure_counts.items())),
        "by_condition": by_condition,
        "inferential_statistics_run": False,
    }


def _numeric(value: object) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _mean(values: Iterable[float | None]) -> float | None:
    usable = [value for value in values if value is not None and math.isfinite(value)]
    if not usable:
        return None
    return sum(usable) / len(usable)
