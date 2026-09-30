"""Fixed-template user request generation for the locked goal conditions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib

from .objectives import ControlledObjective


PROMPT_GENERATOR_VERSION = "1.0.0"


class GoalCondition(StrEnum):
    AMBIGUOUS = "ambiguous"
    EXPLICIT = "explicit"


@dataclass(frozen=True, slots=True)
class UserRequest:
    condition: GoalCondition
    template_id: str
    text: str


_AMBIGUOUS_TEMPLATES = (
    "I need a good laptop for college. I want something affordable, reliable and reasonably sustainable.",
    "I'm looking for a laptop for my studies—ideally affordable, dependable, durable and reasonably sustainable.",
)
_EXPLICIT_PREFIXES = (
    "My priorities, from highest to lowest, are {priorities}.",
    "Please prioritize {priorities}, in that order.",
)
_PRIORITY_LABELS = {
    "price": "lower price",
    "quality": "strong performance and reliability",
    "durability": "long-term durability",
    "sustainability": "sustainability",
}


def generate_request(
    objective: ControlledObjective,
    condition: GoalCondition | str,
    *,
    template_index: int | None = None,
) -> UserRequest:
    """Render a user request without exposing objective weights or profile class.

    Explicit requests state the objective's deterministic priority order and
    hard price cap. Ambiguous requests use one of the locked vague templates.
    """
    try:
        condition = GoalCondition(condition)
    except ValueError as exc:
        raise ValueError(f"Unsupported goal condition: {condition!r}") from exc

    templates = _AMBIGUOUS_TEMPLATES if condition is GoalCondition.AMBIGUOUS else _EXPLICIT_PREFIXES
    index = _template_index(objective, condition, len(templates)) if template_index is None else template_index
    if not 0 <= index < len(templates):
        raise ValueError("template_index is out of range.")

    if condition is GoalCondition.AMBIGUOUS:
        text = templates[index]
    else:
        order = {name: position for position, name in enumerate(_PRIORITY_LABELS)}
        ranked_dimensions = sorted(
            objective.as_dict(),
            key=lambda name: (-objective.weight(name), order[name]),
        )
        priorities = ", then ".join(_PRIORITY_LABELS[name] for name in ranked_dimensions)
        text = templates[index].format(priorities=priorities)
        if objective.hard_max_price_inr is not None:
            text += f" Do not exceed ₹{objective.hard_max_price_inr:,}."
        elif objective.budget_reference_inr is not None:
            text += (
                f" Try to stay under ₹{objective.budget_reference_inr:,} unless a higher-priced "
                "laptop offers a substantial benefit."
            )

    return UserRequest(
        condition=condition,
        template_id=f"{condition.value}-v1-{index + 1:02d}",
        text=text,
    )


def _template_index(objective: ControlledObjective, condition: GoalCondition, size: int) -> int:
    material = f"{PROMPT_GENERATOR_VERSION}:{objective.config_sha256}:{objective.objective_id}:{condition.value}"
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % size
