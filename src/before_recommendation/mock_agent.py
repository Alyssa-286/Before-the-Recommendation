"""Deterministic protocol fixture; it does not access evaluator truth."""

from __future__ import annotations

from dataclasses import dataclass
import json

from .agent_protocol import AgentStart
from .output_parser import OutputParseResult
from .scenarios import AgentScenarioView


MOCK_AGENT_VERSION = "1.0.0"
LOCKED_WEIGHT_KEYS = ("price", "quality", "durability", "sustainability")
DEFAULT_MOCK_WEIGHTS = (("price", 0.35), ("quality", 0.30), ("durability", 0.20), ("sustainability", 0.15))


@dataclass(frozen=True, slots=True)
class MockAgentConfig:
    clarification_needed: bool
    question_target: str = "price"
    preference_weights: tuple[tuple[str, float], ...] = DEFAULT_MOCK_WEIGHTS
    inspect_catalog: bool = True
    emit_malformed_first_response: bool = False

    def __post_init__(self) -> None:
        if self.clarification_needed and not self.question_target.strip():
            raise ValueError("question_target is required for the clarification mock.")
        if self.clarification_needed and self.question_target not in {*LOCKED_WEIGHT_KEYS, "unsupported"}:
            raise ValueError("Use a locked target or 'unsupported' for unsupported/compound questions.")
        if tuple(name for name, _ in self.preference_weights) != LOCKED_WEIGHT_KEYS:
            raise ValueError("Mock weights must use the four locked dimensions in order.")
        if any(value < 0 for _, value in self.preference_weights):
            raise ValueError("Mock weights must be non-negative.")
        if abs(sum(value for _, value in self.preference_weights) - 1.0) > 1e-9:
            raise ValueError("Mock weights must sum to one.")


class DeterministicMockAgent:
    """Exercise the public interface without a network or hidden objective."""

    def __init__(self, config: MockAgentConfig) -> None:
        self.config = config
        self.response_count = 0
        self.recovery_count = 0
        self._last_answer: str | None = None

    def start_trial(self, view: AgentScenarioView) -> AgentStart:
        ids = tuple(listing.product.product_id for listing in view.listings) if self.config.inspect_catalog else ()
        fields = (
            "price", "quality", "durability", "repairability", "sustainability",
            "battery_life", "brand_familiarity", "popularity", "marketing_label",
        ) if self.config.inspect_catalog else ()
        ask = self.config.clarification_needed
        return AgentStart(
            catalog_inspected=self.config.inspect_catalog,
            inspected_product_ids=ids,
            retrieved_fields=fields,
            clarification_needed=ask,
            clarification_question=_question(self.config.question_target) if ask else None,
            question_target=self.config.question_target if ask else None,
        )

    def final_response(self, view: AgentScenarioView, simulated_user_answer: str | None) -> str:
        self.response_count += 1
        self._last_answer = simulated_user_answer
        if self.config.emit_malformed_first_response and self.response_count == 1:
            return "{deterministic mock malformed response"
        return self._serialize(view, simulated_user_answer)

    def recover_invalid_output(self, view: AgentScenarioView, previous: OutputParseResult) -> str:
        self.recovery_count += 1
        return self._serialize(view, self._last_answer)

    def _serialize(self, view: AgentScenarioView, simulated_user_answer: str | None) -> str:
        ask = self.config.clarification_needed
        if ask and (not isinstance(simulated_user_answer, str) or not simulated_user_answer.strip()):
            raise ValueError("Clarification mock expected the environment-provided simulated answer.")
        if not ask and simulated_user_answer is not None:
            raise ValueError("No-clarification mock cannot receive a simulated answer.")

        weights = dict(self.config.preference_weights)
        ranked_ids = sorted(
            (listing.product.product_id for listing in view.listings),
            key=lambda product_id: (-self._public_utility(view, product_id, weights), product_id),
        )
        evidence = ["price", "quality", "durability", "sustainability"]
        if any(listing.marketing_label is not None for listing in view.listings):
            evidence.append("marketing_label")
        payload: dict[str, object] = {
            "catalog_inspected": self.config.inspect_catalog,
            "clarification_needed": ask,
            "clarification_question": _question(self.config.question_target) if ask else None,
            "question_target": self.config.question_target if ask else None,
            "simulated_user_answer": simulated_user_answer if ask else None,
            "preference_weights": weights,
            "ranked_products": ranked_ids,
            "evidence_used": evidence,
            "uncertainty": 0.25 if ask else 0.15,
            "final_explanation": "Deterministic mock output for interface validation only.",
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _public_utility(view: AgentScenarioView, product_id: str, weights: dict[str, float]) -> float:
        product = next(listing.product for listing in view.listings if listing.product.product_id == product_id)
        prices = [listing.product.price_inr for listing in view.listings]
        span = max(prices) - min(prices)
        price_value = 1.0 if span == 0 else (max(prices) - product.price_inr) / span
        return (
            weights["price"] * price_value
            + weights["quality"] * product.quality / 100.0
            + weights["durability"] * product.durability / 100.0
            + weights["sustainability"] * product.sustainability / 100.0
        )


def _question(target: str) -> str:
    return {
        "price": "How important is keeping the price low?",
        "quality": "How important is strong performance and reliability?",
        "durability": "How important is long-term durability?",
        "sustainability": "How important is sustainability?",
        "unsupported": "What is your preference for repairability?",
    }.get(target, f"Could you clarify your preference about {target}?")
