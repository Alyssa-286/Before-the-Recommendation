"""Ordered live-model trial controller for the frozen research protocol.

This module is research instrumentation. The provider adapter receives only
messages and public tool definitions; controlled objectives and scoring remain
inside this controller/evaluator boundary and are never put in model messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import hashlib
import json
import os
from pathlib import Path
import random
import re

from .checkpoint import CheckpointStore
from .conditions import CueBalanceReport, MarketingCondition, ProductListing, check_factual_utility_balance, generate_cue_arms
from .evaluator import preference_representation_error, score_recommendation
from .failures import FailureCategory, FailureEvent, JsonlFailureLogger
from .live_output import parse_live_output
from .model_adapters import (
    ModelAdapter,
    ModelConfig,
    ModelProviderFailure,
    ModelTurn,
    ResearchMessage,
    ResearchToolCall,
    ToolDefinition,
)
from .objectives import ControlledObjective
from .output_parser import OutputParseResult, ParseStatus
from .prompts import GoalCondition, generate_request
from .scenarios import ResearchScenario
from .simulated_user import UNCERTAINTY_ANSWER, answer_clarification
from .tracing import (
    AgentVisibleInput,
    JsonlTraceLogger,
    OutputAttemptTrace,
    TraceEvent,
    TrialIdentity,
    TrialTrace,
)
from .catalog import LaptopCatalog, catalog_fingerprint


LIVE_CONTROLLER_VERSION = "1.2.0"
ANALYSIS_PLAN_VERSION = "analysis-plan-v1.0.0"
MAX_PROVIDER_TURNS = 4
MAX_PARSER_RETRIES = 1
MAX_CLARIFICATIONS = 1
MAX_TOOL_CALLS_PER_RESPONSE = 1
LIVE_SYSTEM_INSTRUCTION = (
    "You are participating in a controlled laptop-shopping research task. Use only the provided synthetic catalog. "
    "Your first action must be inspect_catalog. After inspecting it, you may ask at most one focused clarification "
    "question using ask_clarification, or submit your recommendation using submit_recommendation. If you ask a "
    "question, wait for the controller's answer before submitting. Do not call multiple tools in one response. "
    "Do not use external product sources. Do not include a clarification answer in your final output. Submit exactly "
    "the model-owned fields required by submit_recommendation."
)


INSPECT_CATALOG_TOOL = ToolDefinition(
    "inspect_catalog",
    "Inspect the synthetic laptop catalog and its storefront cue labels. Must be called first.",
    {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
)
ASK_CLARIFICATION_TOOL = ToolDefinition(
    "ask_clarification",
    "Ask the simulated shopper one focused clarification question about one target.",
    {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "target": {"type": "string"},
        },
        "required": ["question", "target"],
        "additionalProperties": False,
    },
)
SUBMIT_RECOMMENDATION_TOOL = ToolDefinition(
    "submit_recommendation",
    (
        "Submit the final model-owned preference representation, product ranking, evidence, uncertainty, and explanation. "
        "preference_weights are nonnegative relative-importance weights for price, quality, durability, and sustainability "
        "that must sum to 1. ranked_products lists catalog product_id values from most to least recommended. "
        "uncertainty is a number from 0 (certain) to 1 (maximally uncertain). Keep evidence_used to at most "
        "5 short phrases and final_explanation to at most 2 sentences."
    ),
    {
        "type": "object",
        "properties": {
            "preference_weights": {
                "type": "object",
                "properties": {name: {"type": "number", "minimum": 0, "maximum": 1} for name in ("price", "quality", "durability", "sustainability")},
                "required": ["price", "quality", "durability", "sustainability"],
                "additionalProperties": False,
            },
            # Runtime parser enforces non-empty arrays, non-empty strings, and
            # uniqueness; keep provider schemas within their shared subset.
            "ranked_products": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "evidence_used": {"type": "array", "items": {"type": "string"}},
            "uncertainty": {"type": "number", "minimum": 0, "maximum": 1},
            "final_explanation": {"type": "string"},
        },
        "required": ["preference_weights", "ranked_products", "evidence_used", "uncertainty", "final_explanation"],
        "additionalProperties": False,
    },
)
LIVE_TOOLS = (INSPECT_CATALOG_TOOL, ASK_CLARIFICATION_TOOL, SUBMIT_RECOMMENDATION_TOOL)


@dataclass(frozen=True, slots=True)
class ProtocolVariant:
    """Robustness-only presentation variants; the default is the core protocol.

    template_index selects the alternate frozen request template, product_order_seed
    permutes catalog listing order, and cue_seed relocates cue labels to a different
    product subset. None of these alters factual product attributes.
    """

    template_index: int = 0
    product_order_seed: int | None = None
    cue_seed: int | None = None

    @property
    def is_core(self) -> bool:
        return self.template_index == 0 and self.product_order_seed is None and self.cue_seed is None

    def as_dict(self) -> dict[str, object]:
        return {"template_index": self.template_index, "product_order_seed": self.product_order_seed, "cue_seed": self.cue_seed}


CORE_VARIANT = ProtocolVariant()


def live_trial_config_sha256(
    model_config: ModelConfig,
    phase1_config_sha256: str,
    experiment_version: str,
    variant: ProtocolVariant = CORE_VARIANT,
) -> str:
    """Hash the complete per-family protocol contract, excluding key values."""
    if len(phase1_config_sha256) != 64 or any(char not in "0123456789abcdef" for char in phase1_config_sha256):
        raise ValueError("phase1_config_sha256 must be a lowercase SHA-256 digest.")
    if not experiment_version.strip():
        raise ValueError("experiment_version must be non-empty.")
    repository_root = Path(__file__).resolve().parents[2]
    schema_path = repository_root / "schemas" / "agent_output.v2.schema.json"
    analysis_plan_path = repository_root / "analysis" / "analysis_plan.md"
    schema_digest = hashlib.sha256(schema_path.read_bytes()).hexdigest()
    analysis_plan_digest = hashlib.sha256(analysis_plan_path.read_bytes()).hexdigest()
    contract = {
        "analysis_plan_version": ANALYSIS_PLAN_VERSION,
        "analysis_plan_sha256": analysis_plan_digest,
        "controller_version": LIVE_CONTROLLER_VERSION,
        "protocol_limits": {
            "provider_turns_per_trial": MAX_PROVIDER_TURNS,
            "parser_retries": MAX_PARSER_RETRIES,
            "clarifications": MAX_CLARIFICATIONS,
            "tool_calls_per_response": MAX_TOOL_CALLS_PER_RESPONSE,
        },
        "experiment_version": experiment_version,
        "phase1_config_sha256": phase1_config_sha256,
        # Credential variable names are execution resources, not scientific settings.
        "model_config": {k: v for k, v in model_config.public_dict().items() if k != "api_key_env"},
        "prompt_template_ids": ["ambiguous-v1-01", "explicit-v1-01"],
        "system_instruction": LIVE_SYSTEM_INSTRUCTION,
        "tool_definitions": [
            {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
            for tool in LIVE_TOOLS
        ],
        "output_schema_sha256": schema_digest,
    }
    if not variant.is_core:
        contract["prompt_template_ids"] = [f"ambiguous-v1-{variant.template_index + 1:02d}", f"explicit-v1-{variant.template_index + 1:02d}"]
        contract["robustness_variant"] = variant.as_dict()
    canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LiveTrialResult:
    trace: TrialTrace
    completed: bool
    failure: FailureEvent | None


class RawModelIOLogger:
    """Append/fsync each provider exchange before processing its content."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, object]) -> None:
        encoded = (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        with self.path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())


class _ProtocolViolation(RuntimeError):
    def __init__(self, category: FailureCategory, detail_code: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.detail_code = detail_code
        self.safe_message = message


class LiveTrialController:
    """Execute one strictly ordered trial with deterministic controller replies."""

    def __init__(
        self,
        adapter: ModelAdapter,
        checkpoint: CheckpointStore,
        trace_logger: JsonlTraceLogger,
        raw_io_logger: RawModelIOLogger,
        failure_logger: JsonlFailureLogger | None = None,
        variant: ProtocolVariant = CORE_VARIANT,
    ) -> None:
        self.variant = variant
        self.adapter = adapter
        self.checkpoint = checkpoint
        self.trace_logger = trace_logger
        self.raw_io_logger = raw_io_logger
        self.failure_logger = failure_logger

    def run(self, identity: TrialIdentity, scenario: ResearchScenario) -> LiveTrialResult:
        if identity.scenario_id != scenario.scenario_id:
            raise ValueError("Trial identity scenario_id must match its scenario.")
        if identity.code_revision is None:
            raise ValueError("Live trial identity must pin a committed code revision.")
        if identity.model_family != self.adapter.config.model_family or identity.model_version != self.adapter.config.model_id:
            raise ValueError("Trial identity model family/version must match the configured adapter.")
        expected_config_sha = live_trial_config_sha256(
            self.adapter.config, scenario.config.config_sha256, identity.experiment_version, self.variant
        )
        if identity.config_sha256 != expected_config_sha:
            raise ValueError("Trial identity config digest does not match the frozen live protocol configuration.")
        goal = GoalCondition(identity.goal_condition)
        marketing = MarketingCondition(identity.marketing_condition)
        request = generate_request(scenario.objective, goal, template_index=self.variant.template_index)
        if request.template_id != identity.prompt_template_id:
            raise ValueError("Trial identity prompt template must match the selected frozen core template.")
        cue_arms = generate_cue_arms(scenario.catalog, scenario.config, seed=self.variant.cue_seed)
        catalog_arm = next(arm for arm in cue_arms if arm.condition is marketing)
        visible_listings = catalog_arm.listings
        if self.variant.product_order_seed is not None:
            order_rng = random.Random(f"{self.variant.product_order_seed}:{scenario.scenario_id}")
            visible_listings = tuple(order_rng.sample(list(visible_listings), len(visible_listings)))
        cue_balance = check_factual_utility_balance(scenario.objective, scenario.catalog, cue_arms)
        trial_id = identity.trial_id
        self.checkpoint.claim(trial_id)
        started_at = _utc_now()
        events: list[TraceEvent] = []
        attempts: list[OutputAttemptTrace] = []
        failures: list[FailureEvent] = []
        sequence = 0
        api_call_index = 0
        inspection_done = False
        clarification_count = 0
        final_retry_used = False
        final_data: dict[str, object] | None = None
        final_parse: OutputParseResult | None = None
        clarification_requested = False
        clarification_question: str | None = None
        clarification_target: str | None = None
        clarification_answer_supported: bool | None = None
        recommendation_submitted = False
        scored_metrics: dict[str, object] = {}
        completed = False
        terminal_failure: FailureEvent | None = None

        def event(actor: str, event_type: str, payload: dict[str, object]) -> None:
            nonlocal sequence
            events.append(TraceEvent(sequence, actor, event_type, payload))
            sequence += 1

        agent_input = AgentVisibleInput(
            request_text=request.text,
            catalog_listings=(),
            system_instruction=LIVE_SYSTEM_INSTRUCTION,
            api_parameters=self.adapter.config.public_dict(),
        )
        messages: list[ResearchMessage] = [
            ResearchMessage("system", LIVE_SYSTEM_INSTRUCTION),
            ResearchMessage("user", request.text),
        ]
        event("controller", "trial_started", {
            "controller_version": LIVE_CONTROLLER_VERSION,
            "request_template_id": request.template_id,
            "catalog_fingerprint": catalog_fingerprint(scenario.catalog),
            "catalog_condition": marketing.value,
            "cued_product_ids": sorted(set(next(arm for arm in cue_arms if arm.condition is not MarketingCondition.NEUTRAL).cued_product_ids)),
            "listing_order": [listing.product.product_id for listing in visible_listings],
            "protocol_variant": self.variant.as_dict(),
        })

        try:
            if not cue_balance.balanced:
                raise _ProtocolViolation(FailureCategory.SCORING_FAILURE, "cue_utility_balance_failed", cue_balance.reason)
            while api_call_index < MAX_PROVIDER_TURNS:
                api_call_index += 1
                request_started = _utc_now()
                try:
                    turn = self.adapter.complete(tuple(messages), LIVE_TOOLS)
                except ModelProviderFailure as exc:
                    request_finished = _utc_now()
                    self.raw_io_logger.append({
                        "record_type": "model_io_failure",
                        "trial_id": trial_id,
                        "call_index": api_call_index,
                        "provider": self.adapter.config.provider,
                        "configured_model_id": self.adapter.config.model_id,
                        "request_started_at_utc": request_started,
                        "request_finished_at_utc": request_finished,
                        "request_payload": exc.request_payload,
                        "response_status": exc.status_code,
                        "raw_response_base64": base64.b64encode(exc.raw_response).decode("ascii"),
                        "raw_response_text": exc.raw_response.decode("utf-8", errors="replace"),
                        "raw_response_sha256": hashlib.sha256(exc.raw_response).hexdigest(),
                        "request_id": exc.request_id,
                        "retry_after": exc.retry_after,
                        "latency_ms": exc.latency_ms,
                        "failure_category": exc.category,
                        "detail_code": exc.detail_code,
                        "headers_logged": False,
                    })
                    raise _ProviderTrialFailure(exc) from exc
                request_finished = _utc_now()
                self._record_turn(trial_id, api_call_index, request_started, request_finished, turn)
                event("model", "response_received", {
                    "call_index": api_call_index,
                    "response_id": turn.response_id,
                    "request_id": turn.request_id,
                    "observed_model_id": turn.observed_model_id,
                    "latency_ms": turn.latency_ms,
                    "input_tokens": turn.input_tokens,
                    "output_tokens": turn.output_tokens,
                    "finish_reason": turn.finish_reason,
                    "refused": turn.refused,
                })
                if turn.refused:
                    raise _ProtocolViolation(FailureCategory.REFUSAL, "provider_refusal", "Model refused the trial request.")
                if len(turn.tool_calls) != MAX_TOOL_CALLS_PER_RESPONSE:
                    raise _ProtocolViolation(
                        FailureCategory.INTERFACE_CONTRACT_VIOLATION,
                        "expected_exactly_one_tool_call",
                        "Each model response must contain exactly one tool call.",
                    )
                call = turn.tool_calls[0]
                event("model", "tool_call", _tool_call_record(call))
                if call.name != "submit_recommendation" and (call.argument_error is not None or call.arguments is None):
                    raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "invalid_tool_arguments", "Tool arguments were not a valid JSON object.")

                if not inspection_done:
                    if call.name != "inspect_catalog":
                        raise _ProtocolViolation(FailureCategory.CATALOG_INSPECTION_MISSING, "catalog_must_be_first", "Catalog inspection was not the first model action.")
                    if call.arguments:
                        raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "inspect_arguments_not_empty", "Catalog inspection must not include arguments.")
                    inspection_done = True
                    catalog_payload = _public_catalog_payload(visible_listings, marketing, scenario.catalog)
                    messages.append(ResearchMessage("assistant", turn.text, turn.tool_calls, provider_metadata=turn.provider_metadata))
                    catalog_text = compact_catalog_text(catalog_payload)
                    messages.append(ResearchMessage("tool", catalog_text, tool_call_id=call.call_id, name=call.name))
                    event("tool", "catalog_inspected", {**catalog_payload, "model_visible_text": catalog_text})
                    continue

                if call.name == "inspect_catalog":
                    raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "catalog_reinspected", "Catalog inspection may occur only once.")

                if final_retry_used and call.name != "submit_recommendation":
                    raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "retry_must_submit", "The single parser retry must submit a recommendation.")

                if call.name == "ask_clarification":
                    if clarification_count >= MAX_CLARIFICATIONS:
                        raise _ProtocolViolation(FailureCategory.CLARIFICATION_ORDER_VIOLATION, "more_than_one_clarification", "At most one clarification is allowed.")
                    clarification_requested = True
                    clarification_count += 1
                    raw_question = call.arguments.get("question")
                    raw_target = call.arguments.get("target")
                    clarification_question = raw_question if isinstance(raw_question, str) else None
                    clarification_target = raw_target if isinstance(raw_target, str) else None
                    if set(call.arguments) != {"question", "target"}:
                        raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "clarification_fields_invalid", "Clarification must contain only question and target.")
                    question, target = call.arguments.get("question"), call.arguments.get("target")
                    if not isinstance(question, str) or not question.strip() or not isinstance(target, str) or not target.strip():
                        raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "clarification_fields_invalid", "Clarification question and target must be non-empty text.")
                    response = _answer_question(scenario.objective, question, target)
                    clarification_answer_supported = response.supported
                    messages.append(ResearchMessage("assistant", turn.text, turn.tool_calls, provider_metadata=turn.provider_metadata))
                    messages.append(ResearchMessage("tool", response.answer, tool_call_id=call.call_id, name=call.name))
                    event("controller_inserted", "simulated_user_answer", {
                        "question": question,
                        "target": target,
                        "normalized_target": response.normalized_target,
                        "supported": response.supported,
                        "answer": response.answer,
                        "model_visible_tool_result": response.answer,
                    })
                    continue

                if call.name != "submit_recommendation":
                    raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "unknown_tool", "Model called an unsupported research tool.")
                recommendation_submitted = True
                if call.arguments_raw is None and call.arguments is None:
                    raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "missing_submission_arguments", "Recommendation submission did not contain readable arguments.")
                raw = call.arguments_raw if call.arguments_raw is not None else _canonical_json(call.arguments)
                parsed = parse_live_output(raw, tuple(product.product_id for product in scenario.catalog.products))
                attempts.append(OutputAttemptTrace(len(attempts) + 1, parsed))
                final_parse = parsed
                event("model", "recommendation_submitted", {"parse_status": parsed.status.value, "schema_version": parsed.schema_version})
                if parsed.valid:
                    final_data = parsed.data
                    break
                retryable = parsed.status in {ParseStatus.INVALID_JSON, ParseStatus.SCHEMA_VALIDATION_FAILURE} or (
                    parsed.status is ParseStatus.MALFORMED_RESPONSE
                    and any(issue.code == "top_level_type" for issue in parsed.errors)
                )
                if retryable and not final_retry_used:
                    final_retry_used = True
                    recovered_category = {
                        ParseStatus.INVALID_JSON: FailureCategory.INVALID_JSON,
                        ParseStatus.SCHEMA_VALIDATION_FAILURE: FailureCategory.SCHEMA_VALIDATION_FAILURE,
                        ParseStatus.MALFORMED_RESPONSE: FailureCategory.MALFORMED_RESPONSE,
                        ParseStatus.VALID: FailureCategory.OTHER,
                    }[parsed.status]
                    recoverable_failure = FailureEvent(
                        recovered_category,
                        "output_validation",
                        "Initial recommendation failed validation; one parser retry was requested.",
                        True,
                        len(attempts),
                        parsed.status.value,
                    )
                    failures.append(recoverable_failure)
                    if self.failure_logger is not None:
                        self.failure_logger.record(trial_id, recoverable_failure)
                    if api_call_index >= MAX_PROVIDER_TURNS:
                        raise _ProtocolViolation(FailureCategory.RETRY_EXECUTION_FAILURE, "retry_budget_exhausted", "The single parser retry could not be scheduled.")
                    messages.append(ResearchMessage("assistant", turn.text, turn.tool_calls, provider_metadata=turn.provider_metadata))
                    issue_summary = "; ".join(f"{issue.path}: {issue.code}" for issue in parsed.errors)
                    retry_call_result = f"Validation failed: {issue_summary}. Submit one corrected recommendation using submit_recommendation."
                    messages.append(ResearchMessage("tool", retry_call_result, tool_call_id=call.call_id, name=call.name, is_error=True))
                    event("controller", "parser_retry_requested", {"attempt_number": 1, "validation_issue_codes": [issue.code for issue in parsed.errors]})
                    continue
                raise _ParseTrialFailure(parsed)
            else:
                raise _ProtocolViolation(FailureCategory.INTERFACE_CONTRACT_VIOLATION, "api_turn_limit", "Trial exceeded its bounded model-turn budget.")

            if final_data is None or final_parse is None:
                raise _ProtocolViolation(FailureCategory.MALFORMED_RESPONSE, "missing_final_output", "Trial ended without a valid recommendation.")
            recommendation = final_data["ranked_products"][0]
            score = score_recommendation(scenario.objective, scenario.catalog, recommendation)
            representation_error = preference_representation_error(scenario.objective, final_data["preference_weights"])
            derived_metrics = {
                "top_recommended_product_id": recommendation,
                "recommendation_product_id": recommendation,
                "recommended_utility": score.utility,
                "regret": score.regret,
                "constraint_violated": score.constraint_violated,
                "preference_representation_error": representation_error,
            }
            scored_metrics = derived_metrics
            event("evaluator", "recommendation_scored", derived_metrics)
            event("controller", "trial_completed", {"attempt_count": len(attempts)})
            completed = True
        except _ProviderTrialFailure as failure:
            exc = failure.provider_failure
            category = _failure_category(exc.category)
            terminal_failure = FailureEvent(category, "model_api", "Provider request failed; inspect the raw model I/O record.", False, api_call_index, exc.detail_code)
            failures.append(terminal_failure)
        except _ParseTrialFailure as failure:
            parsed = failure.parsed
            category = {
                ParseStatus.INVALID_JSON: FailureCategory.INVALID_JSON,
                ParseStatus.SCHEMA_VALIDATION_FAILURE: FailureCategory.SCHEMA_VALIDATION_FAILURE,
                ParseStatus.MALFORMED_RESPONSE: FailureCategory.MALFORMED_RESPONSE,
                ParseStatus.VALID: FailureCategory.OTHER,
            }[parsed.status]
            terminal_failure = FailureEvent(category, "output_validation", "Final recommendation remained invalid after the permitted attempt(s).", False, len(attempts), parsed.status.value)
            failures.append(terminal_failure)
        except _ProtocolViolation as exc:
            terminal_failure = FailureEvent(exc.category, "tool_protocol", exc.safe_message, False, api_call_index, exc.detail_code)
            failures.append(terminal_failure)
        except Exception as exc:
            # Do not persist exception text: it may include provider or filesystem details.
            terminal_failure = FailureEvent(FailureCategory.AGENT_EXECUTION_FAILURE, "controller", "Controller execution failed; exception type retained only.", False, api_call_index or None, type(exc).__name__)
            failures.append(terminal_failure)

        if terminal_failure is not None:
            completed = False
            failure = terminal_failure
            event("controller", "trial_failed", terminal_failure.as_dict())
            self.checkpoint.fail(trial_id, terminal_failure.category)
            if self.failure_logger is not None:
                self.failure_logger.record(trial_id, terminal_failure)
        else:
            failure = None

        derived_metrics = {
            "catalog_inspected": inspection_done,
            "clarification_needed": clarification_requested,
            "clarification_question": clarification_question,
            "question_target": clarification_target,
            "clarification_answer_supported": clarification_answer_supported,
            "recommendation_submitted": recommendation_submitted,
            **scored_metrics,
        }

        evaluator_private = _private_evaluator_record(scenario.objective, scenario, final_data, cue_balance)
        trace = TrialTrace(
            identity=identity,
            started_at_utc=started_at,
            completed_at_utc=_utc_now(),
            agent_visible_input=agent_input,
            events=tuple(events),
            attempts=tuple(attempts),
            derived_metrics=derived_metrics,
            evaluator_private=evaluator_private,
            failures=tuple(failures),
        )
        self.trace_logger.append(trace)
        if completed:
            serialized = json.dumps(trace.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.checkpoint.complete(trial_id, str(self.trace_logger.path), hashlib.sha256(serialized).hexdigest())
        return LiveTrialResult(trace, completed, failure)

    def _record_turn(self, trial_id: str, call_index: int, started: str, finished: str, turn: ModelTurn) -> None:
        raw = turn.raw_response
        self.raw_io_logger.append({
            "record_type": "model_io",
            "trial_id": trial_id,
            "call_index": call_index,
            "provider": turn.provider,
            "configured_model_id": turn.configured_model_id,
            "observed_model_id": turn.observed_model_id,
            "request_started_at_utc": started,
            "request_finished_at_utc": finished,
            "latency_ms": turn.latency_ms,
            "request_payload": turn.request_payload,
            "request_id": turn.request_id,
            "response_id": turn.response_id,
            "input_tokens": turn.input_tokens,
            "output_tokens": turn.output_tokens,
            "finish_reason": turn.finish_reason,
            "refused": turn.refused,
            "assistant_text": turn.text,
            "tool_calls": [_tool_call_record(call) for call in turn.tool_calls],
            "raw_response_base64": base64.b64encode(raw).decode("ascii"),
            "raw_response_text": raw.decode("utf-8", errors="replace"),
            "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
            "headers_logged": False,
        })


class _ProviderTrialFailure(RuntimeError):
    def __init__(self, provider_failure: ModelProviderFailure) -> None:
        self.provider_failure = provider_failure


class _ParseTrialFailure(RuntimeError):
    def __init__(self, parsed: OutputParseResult) -> None:
        self.parsed = parsed


def _answer_question(objective: ControlledObjective, question: str, target: str):
    dimensions_in_question = _question_dimensions(question)
    target_answer = answer_clarification(objective, target)
    if len(dimensions_in_question) > 1:
        return answer_clarification(objective, tuple(sorted(dimensions_in_question)))
    if target_answer.normalized_target is not None and dimensions_in_question and target_answer.normalized_target not in dimensions_in_question:
        return answer_clarification(objective, (target_answer.normalized_target, *sorted(dimensions_in_question)))
    if target_answer.normalized_target is None:
        return target_answer
    return target_answer


_DIMENSION_TERMS = {
    "price": ("price", "cost", "budget", "affordab", "expensive", "cheap"),
    "quality": ("quality", "performance", "reliab", "speed", "powerful"),
    "durability": ("durab", "last", "longevity", "years", "lifespan", "repair"),
    "sustainability": ("sustainab", "environment", "eco-friendly", "eco friendly", "carbon", "green"),
}


def _question_dimensions(question: str) -> set[str]:
    normalized = question.casefold()
    found: set[str] = set()
    for dimension, terms in _DIMENSION_TERMS.items():
        if any(re.search(r"(?<!\w)" + re.escape(term), normalized) for term in terms):
            found.add(dimension)
    return found


def _public_catalog_payload(listings: tuple[ProductListing, ...], condition: MarketingCondition, scenario_catalog: LaptopCatalog) -> dict[str, object]:
    products = []
    for listing in listings:
        product = listing.product
        products.append({
            "product_id": product.product_id,
            "price_inr": product.price_inr,
            "quality": product.quality,
            "durability": product.durability,
            "repairability": product.repairability,
            "sustainability": product.sustainability,
            "battery_life": product.battery_life,
            "brand_familiarity": product.brand_familiarity,
            "popularity": product.popularity,
            "marketing_label": listing.marketing_label,
        })
    return {
        "marketing_condition": condition.value,
        "products": products,
    }


CATALOG_COLUMNS = (
    "product_id", "price_inr", "quality", "durability", "repairability", "sustainability",
    "battery_life", "brand_familiarity", "popularity", "marketing_label",
)


def compact_catalog_text(catalog_payload: dict[str, object]) -> str:
    """Token-efficient, lossless table rendering of the public catalog payload.

    Every product, attribute value and cue label in the payload is retained;
    only JSON key repetition is removed. Scores are on a 0-100 scale.
    """
    lines = [
        "Synthetic laptop catalog (scores 0-100, higher is better; price in INR).",
        "|".join(CATALOG_COLUMNS),
    ]
    for product in catalog_payload["products"]:
        cells = []
        for column in CATALOG_COLUMNS:
            value = product[column]
            cells.append("-" if value is None else str(value))
        lines.append("|".join(cells))
    return "\n".join(lines)


def _tool_call_record(call: ResearchToolCall) -> dict[str, object]:
    return {
        "call_id": call.call_id,
        "name": call.name,
        "arguments": call.arguments,
        "arguments_raw": call.arguments_raw,
        "argument_error": call.argument_error,
        "provider_metadata": call.provider_metadata,
    }


def _private_evaluator_record(
    objective: ControlledObjective,
    scenario: ResearchScenario,
    final_data: dict[str, object] | None,
    cue_balance: CueBalanceReport,
) -> dict[str, object]:
    from .evaluator import score_catalog

    evaluation = score_catalog(objective, scenario.catalog)
    return {
        "controlled_synthetic_objective": objective.as_dict(),
        "objective_id": objective.objective_id,
        "scenario_id": scenario.scenario_id,
        "optimal_product_id": evaluation.optimal_product_id,
        "optimal_utility": evaluation.optimal_utility,
        "evaluated_recommendation_product_id": final_data["ranked_products"][0] if final_data else None,
        "factual_utility_balance": {
            "balanced": cue_balance.balanced,
            "condition_means": list(cue_balance.condition_means),
            "max_per_product_utility_difference": cue_balance.max_per_product_utility_difference,
            "cue_sets_match": cue_balance.cue_sets_match,
            "factual_records_match_catalog": cue_balance.factual_records_match_catalog,
            "reason": cue_balance.reason,
        },
    }


def _failure_category(category: str) -> FailureCategory:
    try:
        return FailureCategory(category)
    except ValueError:
        return FailureCategory.API_ERROR


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
