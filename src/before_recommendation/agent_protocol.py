"""Model-agnostic observable protocol for a one-clarification trial."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .output_parser import OutputParseResult
from .scenarios import AgentScenarioView


AGENT_PROTOCOL_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class AgentStart:
    """Agent's initial observable action, made using only the public scenario view."""

    catalog_inspected: bool
    inspected_product_ids: tuple[str, ...]
    retrieved_fields: tuple[str, ...]
    clarification_needed: bool
    clarification_question: str | None = None
    question_target: str | None = None

    def __post_init__(self) -> None:
        if type(self.catalog_inspected) is not bool or type(self.clarification_needed) is not bool:
            raise ValueError("Protocol decision fields must be booleans.")
        if len(set(self.inspected_product_ids)) != len(self.inspected_product_ids):
            raise ValueError("Inspected product IDs must be unique.")
        if self.clarification_needed:
            if not isinstance(self.clarification_question, str) or not self.clarification_question.strip():
                raise ValueError("A clarification requires non-empty question text.")
            if not isinstance(self.question_target, str) or not self.question_target.strip():
                raise ValueError("A clarification requires an explicit target.")
        elif self.clarification_question is not None or self.question_target is not None:
            raise ValueError("Question and target must be null when clarification is not needed.")


class ResearchAgent(Protocol):
    """Only public request/listings and the simulated answer enter the agent boundary."""

    def start_trial(self, view: AgentScenarioView) -> AgentStart:
        """Inspect public listings and decide whether to ask one clarification."""

    def final_response(self, view: AgentScenarioView, simulated_user_answer: str | None) -> str:
        """Return raw structured-output text after optional clarification."""

    def recover_invalid_output(self, view: AgentScenarioView, previous: OutputParseResult) -> str:
        """Return one replacement after validation feedback, if recovery is needed."""
