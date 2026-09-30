"""Research-side harness for deterministic mock-only protocol validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
from typing import Callable

from .agent_protocol import AgentStart, ResearchAgent
from .checkpoint import CheckpointConflict, CheckpointStore, TrialStatus
from .conditions import MarketingCondition
from .evaluator import preference_representation_error, score_catalog, score_recommendation
from .failures import (
    FailureCategory,
    FailureEvent,
    JsonlFailureLogger,
    category_for_parse_status,
    classify_exception,
)
from .output_parser import OutputParseResult, ParseRun, ParseStatus, parse_with_one_retry
from .prompts import GoalCondition, generate_request
from .scenarios import AgentScenarioView, ResearchScenario
from .simulated_user import answer_clarification
from .tracing import (
    AgentVisibleInput,
    JsonlTraceLogger,
    OutputAttemptTrace,
    TraceEvent,
    TrialIdentity,
    TrialTrace,
)


@dataclass(frozen=True, slots=True)
class TrialRunResult:
    trial_id: str
    status: TrialStatus
    attempts: tuple[OutputParseResult, ...]
    metrics: dict[str, object]
    failures: tuple[FailureEvent, ...]
    trace_record: dict[str, object]
    simulated_user_answer: str | None


def run_mock_interface_trial(
    scenario: ResearchScenario,
    *,
    goal_condition: GoalCondition | str,
    marketing_condition: MarketingCondition | str,
    agent: ResearchAgent,
    checkpoint: CheckpointStore,
    trace_logger: JsonlTraceLogger,
    failure_logger: JsonlFailureLogger,
    model_version: str,
    repetition: int = 1,
) -> TrialRunResult:
    """Run one mock-compatible trial; only ``AgentScenarioView`` reaches the agent.

    Ground truth and all score calculations stay in this harness. It writes one
    append-only trace per claimed trial and uses checkpoint state only after the
    trace is safely appended.
    """
    goal = GoalCondition(goal_condition)
    marketing = MarketingCondition(marketing_condition)
    request = generate_request(scenario.objective, goal)
    view = scenario.agent_view(goal, marketing)
    if view.user_request != request.text:
        raise RuntimeError("Agent view and prompt template rendering diverged.")
    identity = TrialIdentity(
        scenario_id=scenario.scenario_id,
        profile_id=scenario.objective.objective_id,
        goal_condition=goal.value,
        marketing_condition=marketing.value,
        model_family="deterministic_mock",
        model_version=model_version,
        repetition=repetition,
        prompt_template_id=request.template_id,
        experiment_version=scenario.config.experiment_version,
        config_sha256=scenario.config.config_sha256,
        random_seed=scenario.config.objectives_seed,
        code_revision=_source_revision(),
    )
    checkpoint.register_trials((identity,))
    record = checkpoint.get(identity.trial_id)
    if record.status is not TrialStatus.PENDING:
        raise CheckpointConflict(f"Trial {identity.trial_id} is not pending ({record.status.value}).")
    checkpoint.claim(identity.trial_id)

    started_at = _utc_now()
    events: list[TraceEvent] = []
    failures: list[FailureEvent] = []
    attempts: tuple[OutputParseResult, ...] = ()
    metrics: dict[str, object] = {}
    simulated_answer: str | None = None
    agent_start: AgentStart | None = None
    final_status = TrialStatus.FAILED

    def event(actor: str, event_type: str, payload: dict[str, object]) -> None:
        events.append(TraceEvent(len(events), actor, event_type, payload))

    def failure(item: FailureEvent) -> None:
        failures.append(item)
        failure_logger.record(identity.trial_id, item)
        event("harness", "failure_recorded", {"category": item.category.value, "stage": item.stage, "attempt_number": item.attempt_number})

    event("harness", "trial_started", {"scenario_id": scenario.scenario_id, "goal_condition": goal.value, "marketing_condition": marketing.value})
    try:
        agent_start = agent.start_trial(view)
    except Exception as exc:
        failure(FailureEvent(
            classify_exception(exc), "agent_start", f"Agent start raised {type(exc).__name__}.", False,
        ))
    else:
        event("agent", "catalog_inspection", {
            "catalog_inspected": agent_start.catalog_inspected,
            "inspected_product_ids": list(agent_start.inspected_product_ids),
            "retrieved_fields": list(agent_start.retrieved_fields),
        })
        event("agent", "clarification_decision", {"clarification_needed": agent_start.clarification_needed})
        valid_ids = {listing.product.product_id for listing in view.listings}
        if not agent_start.catalog_inspected or not agent_start.inspected_product_ids:
            failure(FailureEvent(
                FailureCategory.CATALOG_INSPECTION_MISSING,
                "catalog_inspection",
                "Agent did not report inspecting any catalog listings.",
                False,
            ))
            if agent_start.clarification_needed:
                failure(FailureEvent(
                    FailureCategory.CLARIFICATION_ORDER_VIOLATION,
                    "clarification",
                    "Clarification was requested before catalog inspection.",
                    False,
                ))
        elif not set(agent_start.inspected_product_ids).issubset(valid_ids):
            failure(FailureEvent(
                FailureCategory.INTERFACE_CONTRACT_VIOLATION,
                "catalog_inspection",
                "Agent reported product IDs outside the trial catalog.",
                False,
            ))
        if agent_start.clarification_needed and not failures:
            event("agent", "clarification_question", {
                "question": agent_start.clarification_question,
                "target": agent_start.question_target,
            })
            response = answer_clarification(scenario.objective, agent_start.question_target or "unsupported")
            simulated_answer = response.answer
            event("simulated_user", "clarification_answer", {
                "requested_target": response.requested_target,
                "normalized_target": response.normalized_target,
                "supported": response.supported,
                "answer": response.answer,
            })

        if not failures:
            try:
                first_raw = agent.final_response(view, simulated_answer)
            except Exception as exc:
                failure(FailureEvent(
                    classify_exception(exc), "agent_final_response", f"Agent response raised {type(exc).__name__}.", False,
                ))
            else:
                event("agent", "raw_response_received", {
                    "attempt_number": 1,
                    "raw_sha256": _raw_sha256(first_raw),
                })

                def retry_provider(previous: OutputParseResult) -> object:
                    event("harness", "validation_retry_requested", {
                        "failed_status": previous.status.value,
                        "validation_errors": [error.code for error in previous.errors],
                    })
                    try:
                        retry_raw = agent.recover_invalid_output(view, previous)
                    except Exception as exc:
                        failure(FailureEvent(
                            classify_exception(exc, retry=True),
                            "validation_retry",
                            f"Recovery response raised {type(exc).__name__}.",
                            False,
                            attempt_number=2,
                        ))
                        raise
                    event("agent", "raw_response_received", {
                        "attempt_number": 2,
                        "raw_sha256": _raw_sha256(retry_raw),
                    })
                    return retry_raw

                parse_run: ParseRun = parse_with_one_retry(
                    first_raw,
                    valid_ids,
                    retry_provider,
                )
                attempts = parse_run.attempts
                for number, parsed in enumerate(attempts, start=1):
                    event("parser", "parse_result", {
                        "attempt_number": number,
                        "status": parsed.status.value,
                        "error_codes": [issue.code for issue in parsed.errors],
                    })
                    category = category_for_parse_status(parsed.status)
                    if category is not None:
                        failure(FailureEvent(
                            category,
                            "output_parse",
                            "Structured output did not satisfy the versioned output contract.",
                            recoverable=(number < len(attempts) and parse_run.final.valid),
                            attempt_number=number,
                        ))

                if parse_run.retry_execution_error:
                    # The retry callback already wrote a typed failure; this event links it to parser state.
                    event("harness", "retry_execution_failed", {"exception_type": parse_run.retry_execution_error})

                final = parse_run.final
                if final.valid and agent_start is not None:
                    violations = _protocol_violations(final.data or {}, agent_start, simulated_answer)
                    for category, detail in violations:
                        failure(FailureEvent(category, "protocol_validation", detail, False))
                    try:
                        weights = final.data["preference_weights"]
                        top_product_id = final.data["ranked_products"][0]
                        score = score_recommendation(scenario.objective, scenario.catalog, top_product_id)
                        evaluation = score_catalog(scenario.objective, scenario.catalog)
                        representation_error = preference_representation_error(scenario.objective, weights)
                        metrics = {
                            "preference_representation_error": representation_error,
                            "top_recommended_product_id": top_product_id,
                            "recommended_utility": score.utility,
                            "optimal_product_id": evaluation.optimal_product_id,
                            "optimal_utility": evaluation.optimal_utility,
                            "regret": score.regret,
                            "constraint_violated": score.constraint_violated,
                        }
                        event("evaluator", "trial_scored", metrics.copy())
                    except Exception as exc:
                        failure(FailureEvent(
                            FailureCategory.SCORING_FAILURE,
                            "evaluation",
                            f"Deterministic scoring raised {type(exc).__name__}.",
                            False,
                        ))
                if final.valid and not any(not item.recoverable for item in failures):
                    final_status = TrialStatus.COMPLETED

    if final_status is TrialStatus.COMPLETED:
        event("harness", "trial_completed", {"trial_id": identity.trial_id})
    else:
        event("harness", "trial_failed", {"trial_id": identity.trial_id})

    evaluation = score_catalog(scenario.objective, scenario.catalog)
    listings = tuple(_listing_record(view, listing) for listing in view.listings)
    trace = TrialTrace(
        identity=identity,
        started_at_utc=started_at,
        completed_at_utc=_utc_now(),
        agent_visible_input=AgentVisibleInput(view.user_request, listings),
        events=tuple(events),
        attempts=tuple(OutputAttemptTrace(number, parsed) for number, parsed in enumerate(attempts, start=1)),
        derived_metrics=metrics,
        evaluator_private={
            "data_type": "controlled_synthetic_objective",
            "objective_id": scenario.objective.objective_id,
            "profile_class": scenario.objective.profile_class,
            "weights": scenario.objective.as_dict(),
            "hard_max_price_inr": scenario.objective.hard_max_price_inr,
            "soft_budget_reference_inr": scenario.objective.budget_reference_inr,
            "optimal_product_id": evaluation.optimal_product_id,
            "optimal_utility": evaluation.optimal_utility,
        },
        failures=tuple(failures),
    )
    trace_record = trace.as_dict()
    trace_logger.append(trace)
    if final_status is TrialStatus.COMPLETED:
        checkpoint.complete(identity.trial_id, f"{Path(trace_logger.path).as_posix()}#{identity.trial_id}")
    else:
        checkpoint.fail(identity.trial_id, failures[-1].category if failures else FailureCategory.OTHER)
    return TrialRunResult(
        identity.trial_id,
        final_status,
        attempts,
        metrics,
        tuple(failures),
        trace_record,
        simulated_answer,
    )


def _protocol_violations(
    output: dict[str, object],
    start: AgentStart,
    simulated_answer: str | None,
) -> tuple[tuple[FailureCategory, str], ...]:
    violations: list[tuple[FailureCategory, str]] = []
    expected_fields = {
        "catalog_inspected": start.catalog_inspected,
        "clarification_needed": start.clarification_needed,
        "clarification_question": start.clarification_question,
        "question_target": start.question_target,
        "simulated_user_answer": simulated_answer,
    }
    for key, expected in expected_fields.items():
        if output.get(key) != expected:
            category = (
                FailureCategory.SIMULATED_ANSWER_MISMATCH
                if key == "simulated_user_answer"
                else FailureCategory.INTERFACE_CONTRACT_VIOLATION
            )
            violations.append((category, f"Structured output field {key!r} does not match the observable interface event."))
    return tuple(violations)


def _listing_record(view: AgentScenarioView, listing: object) -> dict[str, object]:
    # Listing is a ProductListing; keep type conversion local to the research log.
    return {**asdict(listing.product), "marketing_label": listing.marketing_label}


def _raw_sha256(raw_output: object) -> str | None:
    if not isinstance(raw_output, str):
        return None
    return hashlib.sha256(raw_output.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _source_revision() -> str | None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None
