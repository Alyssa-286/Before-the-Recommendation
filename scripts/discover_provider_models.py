"""List currently accessible model IDs without recording credentials."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from before_recommendation.runtime_config import load_runtime_environment


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "model_access_matrix.json"
NAMES = ("OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY")


def _presence(name: str) -> str:
    value = os.environ.get(name)
    return "SET" if isinstance(value, str) and value.strip() else "NOT SET"


def _sanitize(text: str) -> str:
    for name in NAMES:
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def _get(url: str, headers: dict[str, str], timeout: float = 45.0) -> tuple[int, object, dict[str, str]]:
    request = Request(url, headers={"User-Agent": "before-the-recommendation-research/0.1", **headers}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            header_map = {key.lower(): value for key, value in response.headers.items()}
            status = response.status
    except HTTPError as exc:
        body = exc.read()
        header_map = {key.lower(): value for key, value in (exc.headers.items() if exc.headers else [])}
        status = exc.code
    except URLError as exc:
        return 0, {"error": _sanitize(str(exc.reason or exc))}, {}
    except TimeoutError:
        return 0, {"error": "timeout"}, {}
    text = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {"non_json_body": True, "body_preview": _sanitize(text)[:400]}
    interesting = {
        key: header_map[key]
        for key in (
            "x-ratelimit-limit-requests",
            "x-ratelimit-limit-tokens",
            "x-ratelimit-remaining-requests",
            "x-ratelimit-remaining-tokens",
            "retry-after",
            "x-request-id",
        )
        if key in header_map
    }
    return status, payload, interesting


def _openai_ids(payload: object) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return []
    ids = []
    for item in payload["data"]:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return sorted(ids)


def _gemini_ids(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        return []
    models = []
    for item in payload["models"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        name = item["name"].removeprefix("models/")
        methods = item.get("supportedGenerationMethods") if isinstance(item.get("supportedGenerationMethods"), list) else []
        models.append({
            "exact_model_id": name,
            "display_name": item.get("displayName"),
            "supported_generation_methods": methods,
            "input_token_limit": item.get("inputTokenLimit"),
            "output_token_limit": item.get("outputTokenLimit"),
        })
    return sorted(models, key=lambda row: str(row["exact_model_id"]))


def _groq_models(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return []
    models = []
    for item in payload["data"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        models.append({
            "exact_model_id": item["id"],
            "owned_by": item.get("owned_by"),
            "context_window": item.get("context_window"),
            "max_completion_tokens": item.get("max_completion_tokens"),
        })
    return sorted(models, key=lambda row: str(row["exact_model_id"]))


def main() -> None:
    load_runtime_environment(names=NAMES)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    credential_presence = {name: _presence(name) for name in NAMES}

    openai_status, openai_payload, openai_headers = (None, None, {})
    gemini_status, gemini_payload, gemini_headers = (None, None, {})
    groq_status, groq_payload, groq_headers = (None, None, {})

    if credential_presence["OPENAI_API_KEY"] == "SET":
        openai_status, openai_payload, openai_headers = _get(
            "https://api.openai.com/v1/models",
            {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        )
    if credential_presence["GEMINI_API_KEY"] == "SET":
        gemini_status, gemini_payload, gemini_headers = _get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            {"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        )
    if credential_presence["GROQ_API_KEY"] == "SET":
        groq_status, groq_payload, groq_headers = _get(
            "https://api.groq.com/openai/v1/models",
            {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        )

    openai_ids = _openai_ids(openai_payload) if openai_status == 200 else []
    gemini_models = _gemini_ids(gemini_payload) if gemini_status == 200 else []
    groq_models = _groq_models(groq_payload) if groq_status == 200 else []

    chat_like = [
        model_id
        for model_id in openai_ids
        if any(token in model_id for token in ("gpt-", "o1", "o3", "o4", "chatgpt"))
        and "audio" not in model_id
        and "realtime" not in model_id
        and "transcribe" not in model_id
        and "tts" not in model_id
        and "image" not in model_id
        and "search" not in model_id
    ]

    artifact = {
        "artifact_version": "model-access-matrix-v2.0.0",
        "observed_at_utc": observed_at,
        "repository": "Alyssa-286/Before-the-Recommendation",
        "candidate_policy": {
            "candidate_providers": ["OpenAI", "Google Gemini", "Groq"],
            "excluded_by_current_instruction": ["Anthropic/Claude"],
            "selection_objective": "minimize expected total API cost for the frozen 1,920-run experiment subject to two distinct model families and technical validity",
        },
        "credential_variable_presence": credential_presence,
        "credential_values_printed_or_recorded": False,
        "dotenv_loader_used": True,
        "live_list_requests_made": sum(status is not None for status in (openai_status, gemini_status, groq_status)),
        "providers": [
            {
                "provider": "OpenAI",
                "credential_environment_variable": "OPENAI_API_KEY",
                "credential_available": credential_presence["OPENAI_API_KEY"] == "SET",
                "adapter_available": True,
                "adapter": "openai_chat_completions",
                "list_endpoint": "https://api.openai.com/v1/models",
                "list_http_status": openai_status,
                "rate_limit_headers_observed": openai_headers,
                "accessible_model_ids": openai_ids,
                "chat_like_model_ids": chat_like,
                "list_error": None if openai_status == 200 else openai_payload,
            },
            {
                "provider": "Google Gemini",
                "credential_environment_variable": "GEMINI_API_KEY",
                "credential_available": credential_presence["GEMINI_API_KEY"] == "SET",
                "adapter_available": True,
                "adapter": "gemini_openai_compat",
                "list_endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
                "list_http_status": gemini_status,
                "rate_limit_headers_observed": gemini_headers,
                "accessible_models": gemini_models,
                "list_error": None if gemini_status == 200 else gemini_payload,
            },
            {
                "provider": "Groq",
                "credential_environment_variable": "GROQ_API_KEY",
                "credential_available": credential_presence["GROQ_API_KEY"] == "SET",
                "adapter_available": True,
                "adapter": "groq_chat_completions",
                "list_endpoint": "https://api.groq.com/openai/v1/models",
                "list_http_status": groq_status,
                "rate_limit_headers_observed": groq_headers,
                "accessible_models": groq_models,
                "list_error": None if groq_status == 200 else groq_payload,
            },
        ],
        "official_pricing_sources": {
            "openai": "https://developers.openai.com/api/docs/pricing",
            "openai_gpt_5_nano": "https://developers.openai.com/api/docs/models/gpt-5-nano",
            "openai_gpt_4.1_nano": "https://developers.openai.com/api/docs/models/gpt-4.1-nano",
            "openai_gpt_4o_mini": "https://developers.openai.com/api/docs/models/gpt-4o-mini",
            "gemini": "https://ai.google.dev/gemini-api/docs/pricing",
            "gemini_rate_limits": "https://ai.google.dev/gemini-api/docs/rate-limits",
            "groq_models": "https://console.groq.com/docs/models",
            "groq_gpt_oss_20b": "https://console.groq.com/docs/model/openai/gpt-oss-20b",
            "groq_rate_limits": "https://console.groq.com/docs/rate-limits",
        },
        "documented_prices_per_1m_tokens_usd_standard": {
            "gpt-5-nano": {"input": 0.05, "output": 0.40, "source": "https://developers.openai.com/api/docs/models/gpt-5-nano", "retrieved_on": "2026-10-01"},
            "gpt-4.1-nano": {"input": 0.10, "output": 0.40, "source": "https://developers.openai.com/api/docs/models/gpt-4.1-nano", "retrieved_on": "2026-10-01"},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60, "source": "https://developers.openai.com/api/docs/models/gpt-4o-mini", "retrieved_on": "2026-10-01"},
            "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40, "free_tier_tokens": "free of charge while within documented free-tier limits", "source": "https://ai.google.dev/gemini-api/docs/pricing", "retrieved_on": "2026-10-01"},
            "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50, "free_tier_tokens": "free of charge while within documented free-tier limits", "source": "https://ai.google.dev/gemini-api/docs/pricing", "retrieved_on": "2026-10-01"},
            "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50, "free_tier_tokens": "free of charge while within documented free-tier limits", "source": "https://ai.google.dev/gemini-api/docs/pricing", "retrieved_on": "2026-10-01"},
            "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30, "source": "https://console.groq.com/docs/model/openai/gpt-oss-20b", "retrieved_on": "2026-10-01"},
            "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60, "source": "https://console.groq.com/docs/models", "retrieved_on": "2026-10-01"},
            "qwen/qwen3.8-27b": {"input": 0.80, "output": 4.00, "source": "https://console.groq.com/docs/models", "retrieved_on": "2026-10-01"},
        },
        "notes": [
            "Credential values were not written to this artifact.",
            "Model IDs below are those returned by the authenticated list endpoints at observation time.",
            "Pricing is copied from official provider documentation retrieved 2026-10-01 and is not a live billing quote.",
            "Free-tier access is not treated as unlimited.",
            "Anthropic/Claude remains excluded.",
        ],
    }
    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("OPENAI_API_KEY:", credential_presence["OPENAI_API_KEY"])
    print("GEMINI_API_KEY:", credential_presence["GEMINI_API_KEY"])
    print("GROQ_API_KEY:", credential_presence["GROQ_API_KEY"])
    print("openai_list_status:", openai_status, "n_ids:", len(openai_ids), "n_chat_like:", len(chat_like))
    print("gemini_list_status:", gemini_status, "n_models:", len(gemini_models))
    print("groq_list_status:", groq_status, "n_models:", len(groq_models))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
