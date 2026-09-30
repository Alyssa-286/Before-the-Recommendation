"""Automated ground-truth isolation check over model-visible request payloads.

Only content the controller sends to a provider (system, user and tool
messages) is inspected; the model's own assistant turns are excluded because
they cannot leak evaluator data. Any hit means the instrument is contaminated.
"""

from __future__ import annotations

import json
import re

from .evaluator import score_catalog
from .scenarios import ResearchScenario


FORBIDDEN_TERMS = (
    "controlled_synthetic_objective",
    "latent",
    "optimal",
    "utility",
    "regret",
    "objective_id",
    "OBJECTIVE_",
    "profile_class",
    "budget_oriented",
    "quality_oriented",
    "durability_oriented",
    "sustainability_oriented",
    "evaluator",
    "counterfactual",
)


def _visible_text(request_payload: dict[str, object]) -> str:
    parts: list[str] = []
    messages = request_payload.get("messages") if isinstance(request_payload, dict) else None
    for message in messages or []:
        if not isinstance(message, dict) or message.get("role") == "assistant":
            continue
        content = message.get("content")
        parts.append(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False))
    if request_payload.get("tools") is not None:
        parts.append(json.dumps(request_payload["tools"], ensure_ascii=False))
    if isinstance(request_payload.get("system"), str):
        parts.append(str(request_payload["system"]))
    return "\n".join(parts)


def check_request_payload(request_payload: dict[str, object], scenario: ResearchScenario) -> list[str]:
    """Return a list of leakage findings (empty means clean)."""
    text = _visible_text(request_payload)
    lowered = text.casefold()
    findings = [f"term:{term}" for term in FORBIDDEN_TERMS if term.casefold() in lowered]
    for name, weight in scenario.objective.weights:
        for rendered in {repr(weight), f"{weight:.4f}", f"{weight:.3f}"}:
            if len(rendered.split(".")[-1]) >= 3 and re.search(r"(?<![\d.])" + re.escape(rendered) + r"(?!\d)", text):
                findings.append(f"weight_value:{name}")
    evaluation = score_catalog(scenario.objective, scenario.catalog)
    optimal = f"{evaluation.optimal_utility:.6f}"
    if optimal in text:
        findings.append("optimal_utility_value")
    return sorted(set(findings))
