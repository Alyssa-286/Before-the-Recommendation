"""Model settings and stage definitions for the live pilot and core experiment.

The selected pair is the lowest-cost eligible model-family pair under the
predefined experimental constraints (see artifacts/model_selection.json).
Settings are uniform across families: provider-default sampling temperature,
4,096 maximum output tokens, 120 s timeout. ``reasoning_effort="low"`` is the
lowest level the Groq gpt-oss endpoint documents; Gemini uses its default.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model_adapters import ModelConfig


_COMMON = dict(temperature=None, max_output_tokens=4096, timeout_seconds=120.0)

SELECTED_MODELS: dict[str, ModelConfig] = {
    "google_gemini": ModelConfig(
        "gemini_openai_compat", "gemini-3.1-flash-lite", "google_gemini", "GEMINI_API_KEY", **_COMMON
    ),
    "openai_gpt_oss": ModelConfig(
        "groq_chat_completions", "openai/gpt-oss-20b", "openai_gpt_oss", "GROQ_API_KEY",
        reasoning_effort="low", **_COMMON,
    ),
}

# Client-side pacing per model (seconds between request starts) and worker count.
PACING: dict[str, tuple[float, int]] = {
    "google_gemini": (4.5, 2),
    "openai_gpt_oss": (14.0, 1),
}

GOALS = ("ambiguous", "explicit")
MARKETINGS = ("neutral", "scarcity", "social_proof", "discount")


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    experiment_version: str
    scenario_ids: tuple[str, ...]
    repetitions: tuple[int, ...]
    counts_as_core_data: bool


STAGES = {
    "pilot": Stage("pilot", "live-pilot-v1", ("SCENARIO_003", "SCENARIO_004"), (1,), False),
    "core": Stage("core", "core-v1.0.0", tuple(f"SCENARIO_{i:03d}" for i in range(1, 41)), (1, 2, 3), True),
}
