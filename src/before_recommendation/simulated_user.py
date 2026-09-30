"""Deterministic answers to supported single-target clarification questions."""

from __future__ import annotations

from dataclasses import dataclass

from .objectives import ControlledObjective


SIMULATED_USER_VERSION = "1.0.0"
UNCERTAINTY_ANSWER = "I'm not sure; I haven't specified a preference on that point."
SUPPORTED_TARGETS = ("price", "quality", "durability", "sustainability")

_TARGET_ALIASES = {
    "price": "price",
    "cost": "price",
    "budget": "price",
    "affordability": "price",
    "quality": "quality",
    "performance": "quality",
    "quality performance": "quality",
    "performance quality": "quality",
    "durability": "durability",
    "longevity": "durability",
    "sustainability": "sustainability",
    "environmental sustainability": "sustainability",
}
_TARGET_LABELS = {
    "price": "Price",
    "quality": "Reliable performance for college work",
    "durability": "A laptop that lasts for several years",
    "sustainability": "Sustainability",
}


@dataclass(frozen=True, slots=True)
class SimulatedResponse:
    requested_target: str
    normalized_target: str | None
    supported: bool
    answer: str


def answer_clarification(
    objective: ControlledObjective,
    target: str | tuple[str, ...] | list[str],
) -> SimulatedResponse:
    """Answer one supported target from the controlled objective.

    Compound, unsupported, and unknown targets receive the same standardized
    uncertainty response, as specified in the project lock.
    """
    requested = ", ".join(target) if isinstance(target, (tuple, list)) else str(target)
    if isinstance(target, (tuple, list)) and len(target) != 1:
        return _uncertain(requested)
    if not isinstance(target, str) and not isinstance(target, (tuple, list)):
        return _uncertain(requested)
    raw_target = target[0] if isinstance(target, (tuple, list)) and target else target
    if not isinstance(raw_target, str):
        return _uncertain(requested)
    key = " ".join(raw_target.casefold().replace("_", " ").replace("-", " ").split())
    normalized = _TARGET_ALIASES.get(key)
    if normalized is None:
        return _uncertain(requested)

    ranking = sorted(objective.as_dict(), key=lambda name: (-objective.weight(name), SUPPORTED_TARGETS.index(name)))
    rank = ranking.index(normalized)
    if rank == 0:
        answer = _top_priority_answer(objective, normalized)
    else:
        higher_priorities = " and ".join(_TARGET_LABELS[name].lower() for name in ranking[:rank])
        answer = f"{_TARGET_LABELS[normalized]} matters to me, but I prioritize {higher_priorities} more."
    return SimulatedResponse(requested, normalized, True, answer)


def _top_priority_answer(objective: ControlledObjective, target: str) -> str:
    if target == "price":
        if objective.hard_max_price_inr is not None:
            return f"Price matters most to me; please do not exceed ₹{objective.hard_max_price_inr:,}."
        if objective.budget_reference_inr is not None:
            return (
                f"Price matters most to me; please try to stay under ₹{objective.budget_reference_inr:,} "
                "unless a higher-priced laptop offers a substantial benefit."
            )
        return "Price matters most to me."
    if target == "quality":
        return "Reliable performance for college work matters most to me."
    if target == "durability":
        return "I care most about a laptop lasting for several years."
    return "Sustainability matters most to me."


def _uncertain(requested: str) -> SimulatedResponse:
    return SimulatedResponse(requested, None, False, UNCERTAINTY_ANSWER)
