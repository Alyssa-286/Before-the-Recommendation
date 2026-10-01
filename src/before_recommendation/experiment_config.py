"""Model settings, credential pools and stage definitions for live execution.

Selected pair (artifacts/model_selection.json, v2): lowest-cost eligible model-family
pair under the predefined experimental constraints with a strict INR 0 budget:
Google ``gemini-3.1-flash-lite`` and Mistral ``ministral-14b-2512``. Both run on
verified free routes (Gemini FreeTier quota IDs observed; Mistral Free mode).
Settings are uniform across families: provider-default sampling temperature,
4,096 maximum output tokens, 120 s timeout, no reasoning-effort override.

Credential pools are execution resources for ONE model each. Gemini keys 2 and 3
are separate FreeTier projects; GEMINI_API_KEY is excluded because its free-tier
status could not be confirmed. The two Mistral keys share one workspace quota, so
only one is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .live_controller import CORE_VARIANT, ProtocolVariant
from .model_adapters import ModelConfig


# Corrected environment (catalog-acceptance-v1.0.0); configs/phase1.json is preserved.
CORE_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "core_v2.json"

_COMMON = dict(temperature=None, max_output_tokens=4096, timeout_seconds=120.0)

SELECTED_MODELS: dict[str, ModelConfig] = {
    "google_gemini": ModelConfig(
        "gemini_openai_compat", "gemini-3.1-flash-lite", "google_gemini", "GEMINI_API_KEY_2", **_COMMON
    ),
    "mistral": ModelConfig(
        "mistral_chat_completions", "ministral-14b-2512", "mistral", "MISTRAL_API_KEY", **_COMMON
    ),
}

CREDENTIAL_POOLS: dict[str, tuple[str, ...]] = {
    "google_gemini": ("GEMINI_API_KEY_2", "GEMINI_API_KEY_3"),
    "mistral": ("MISTRAL_API_KEY",),
}

# Seconds between request starts PER CREDENTIAL, and concurrent trial workers.
# Gemini FreeTier: 15 RPM per project observed -> 12 RPM per credential.
# Mistral Free mode: 30 RPM for ministral-14b observed (shared workspace) -> 24 RPM.
PACING: dict[str, tuple[float, int]] = {
    "google_gemini": (5.0, 4),
    "mistral": (2.5, 3),
}

GOALS = ("ambiguous", "explicit")
MARKETINGS = ("neutral", "scarcity", "social_proof", "discount")
ALL_SCENARIOS = tuple(f"SCENARIO_{i:03d}" for i in range(1, 41))


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    experiment_version: str
    scenario_ids: tuple[str, ...]
    repetitions: tuple[int, ...]
    counts_as_core_data: bool
    goals: tuple[str, ...] = GOALS
    variant: ProtocolVariant = CORE_VARIANT


STAGES = {
    "pilot": Stage("pilot", "live-pilot-v1", ("SCENARIO_003", "SCENARIO_004"), (1,), False),
    # Infrastructure-only token measurement of controller v1.2 on the corrected catalog (not research data).
    "token_measurement": Stage("token_measurement", "token-measurement-v1", ("SCENARIO_005",), (1,), False),
    # Final infrastructure pilot with the frozen pair, controller and catalog (not research data).
    "pilot_v2": Stage("pilot_v2", "live-pilot-v2", ("SCENARIO_003", "SCENARIO_004"), (1,), False),
    "core": Stage("core", "core-v2.0.0", ALL_SCENARIOS, (1, 2, 3), True),
    # Robustness datasets (analysis plan section 6), frozen before core data: ambiguous goal,
    # all 40 scenarios, 4 marketing arms, both models, 1 repetition each; separate from the core.
    "robust_template": Stage("robust_template", "robust-template-v1", ALL_SCENARIOS, (1,), False, ("ambiguous",), ProtocolVariant(template_index=1)),
    "robust_order": Stage("robust_order", "robust-order-v1", ALL_SCENARIOS, (1,), False, ("ambiguous",), ProtocolVariant(product_order_seed=20261003)),
    "robust_cue_location": Stage("robust_cue_location", "robust-cue-location-v1", ALL_SCENARIOS, (1,), False, ("ambiguous",), ProtocolVariant(cue_seed=20261004)),
}
