"""Small, secret-safe HTTP adapters for supported research model APIs.

The adapters expose only one provider-neutral completion contract. They do
not select models, perform retries, access the internet on a model's behalf,
or execute tools. The live trial controller owns tool sequencing.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
import re
from time import perf_counter
from typing import Callable, Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODEL_ADAPTER_VERSION = "1.0.0"
ANTHROPIC_API_VERSION = "2023-06-01"

ProviderName = Literal["openai_chat_completions", "anthropic_messages"]

_ENDPOINTS: dict[ProviderName, str] = {
    "openai_chat_completions": "https://api.openai.com/v1/chat/completions",
    "anthropic_messages": "https://api.anthropic.com/v1/messages",
}


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Reproducible public model settings; credentials remain in environment."""

    provider: ProviderName
    model_id: str
    model_family: str
    api_key_env: str
    temperature: float | None = 0.0
    seed: int | None = None
    max_output_tokens: int = 1200
    timeout_seconds: float = 90.0

    def __post_init__(self) -> None:
        if self.provider not in _ENDPOINTS:
            raise ValueError("Unsupported provider adapter.")
        if not self.model_id.strip() or not self.model_family.strip() or not self.api_key_env.strip():
            raise ValueError("Model ID, family label, and credential environment-variable name are required.")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env) is None:
            raise ValueError("api_key_env must be an environment-variable name, never a credential value.")
        if self.temperature is not None and (type(self.temperature) not in (int, float) or not math.isfinite(float(self.temperature)) or not 0 <= self.temperature <= 2):
            raise ValueError("temperature must be null or in [0, 2].")
        if self.provider == "anthropic_messages" and self.temperature is not None and self.temperature > 1:
            raise ValueError("Anthropic temperature must be null or in [0, 1].")
        if self.seed is not None and (type(self.seed) is not int or self.seed < 0):
            raise ValueError("seed must be null or a non-negative integer.")
        if self.provider == "anthropic_messages" and self.seed is not None:
            raise ValueError("The Anthropic Messages adapter has no seed parameter.")
        if (
            type(self.max_output_tokens) is not int
            or self.max_output_tokens < 1
            or type(self.timeout_seconds) not in (int, float)
            or not math.isfinite(float(self.timeout_seconds))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("Token and timeout limits must be positive.")

    @property
    def endpoint(self) -> str:
        return _ENDPOINTS[self.provider]

    @property
    def structured_output_mode(self) -> str:
        if self.provider == "openai_chat_completions":
            return "strict_function_tool_schema"
        return "messages_tool_input_schema"

    def public_dict(self) -> dict[str, object]:
        """Return hashable configuration metadata without a credential value."""
        return {
            "adapter_version": MODEL_ADAPTER_VERSION,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "model_id": self.model_id,
            "model_family": self.model_family,
            "api_key_env": self.api_key_env,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "structured_output_mode": self.structured_output_mode,
            "provider_api_version": ANTHROPIC_API_VERSION if self.provider == "anthropic_messages" else None,
        }

    @property
    def config_sha256(self) -> str:
        serialized = json.dumps(self.public_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ResearchToolCall:
    call_id: str
    name: str
    arguments: dict[str, object] | None
    arguments_raw: str | None
    argument_error: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchMessage:
    """Provider-neutral message used by the ordered tool controller."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: tuple[ResearchToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None
    is_error: bool = False

    def __post_init__(self) -> None:
        if self.role == "tool" and not self.tool_call_id:
            raise ValueError("Tool result messages require tool_call_id.")
        if self.role != "assistant" and self.tool_calls:
            raise ValueError("Only assistant messages can contain tool calls.")


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, object]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Tool name and description are required.")
        if self.input_schema.get("type") != "object":
            raise ValueError("Tool input schema must be a JSON object schema.")


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    body: bytes
    request_id: str | None = None
    retry_after: str | None = None


class HttpTransport(Protocol):
    def __call__(self, endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
        """Send one HTTPS JSON request. Implementations must not log headers."""


@dataclass(frozen=True, slots=True)
class ModelTurn:
    provider: ProviderName
    configured_model_id: str
    observed_model_id: str | None
    response_id: str | None
    request_id: str | None
    request_payload: dict[str, object]
    raw_response: bytes
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    text: str | None
    tool_calls: tuple[ResearchToolCall, ...]
    finish_reason: str | None
    refused: bool


class ModelProviderFailure(RuntimeError):
    """Sanitized transport/API failure; never formats request headers or keys."""

    def __init__(
        self,
        category: str,
        detail_code: str,
        *,
        status_code: int | None = None,
        raw_response: bytes = b"",
        request_payload: dict[str, object] | None = None,
        request_id: str | None = None,
        retry_after: str | None = None,
        latency_ms: float | None = None,
    ) -> None:
        super().__init__(f"{category}:{detail_code}")
        self.category = category
        self.detail_code = detail_code
        self.status_code = status_code
        self.raw_response = raw_response
        self.request_payload = request_payload or {}
        self.request_id = request_id
        self.retry_after = retry_after
        self.latency_ms = latency_ms


class _DuplicateJSONKeyError(ValueError):
    pass


class ModelAdapter(Protocol):
    config: ModelConfig

    def complete(
        self,
        messages: tuple[ResearchMessage, ...],
        tools: tuple[ToolDefinition, ...],
    ) -> ModelTurn:
        """Request one observable model turn without executing any tool."""


def make_adapter(config: ModelConfig, transport: HttpTransport | None = None) -> ModelAdapter:
    actual_transport = transport or _http_post_json
    if config.provider == "openai_chat_completions":
        return OpenAIChatCompletionsAdapter(config, actual_transport)
    if config.provider == "anthropic_messages":
        return AnthropicMessagesAdapter(config, actual_transport)
    raise ValueError("Unsupported provider adapter.")


class _BaseAdapter:
    def __init__(self, config: ModelConfig, transport: HttpTransport) -> None:
        self.config = config
        self._transport = transport

    def _credential(self) -> str:
        value = os.environ.get(self.config.api_key_env)
        if not value:
            raise ModelProviderFailure("api_error", "missing_credential")
        return value

    def _request(
        self,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> tuple[HttpResponse, float]:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        started = perf_counter()
        try:
            response = self._transport(self.config.endpoint, headers, body, self.config.timeout_seconds)
        except TimeoutError as exc:
            raise ModelProviderFailure("timeout", "transport_timeout", request_payload=payload, latency_ms=(perf_counter() - started) * 1000) from exc
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            category = "timeout" if isinstance(reason, TimeoutError) else "api_error"
            detail = "transport_timeout" if category == "timeout" else "transport_error"
            raise ModelProviderFailure(category, detail, request_payload=payload, latency_ms=(perf_counter() - started) * 1000) from exc
        except OSError as exc:
            category = "timeout" if isinstance(exc, TimeoutError) else "api_error"
            detail = "transport_timeout" if category == "timeout" else "transport_error"
            raise ModelProviderFailure(category, detail, request_payload=payload, latency_ms=(perf_counter() - started) * 1000) from exc
        latency_ms = (perf_counter() - started) * 1000
        if not 200 <= response.status_code < 300:
            category = "rate_limit" if response.status_code == 429 else "timeout" if response.status_code in {408, 504} else "api_error"
            detail = "rate_limit" if category == "rate_limit" else "http_error"
            raise ModelProviderFailure(
                category,
                detail,
                status_code=response.status_code,
                raw_response=response.body,
                request_payload=payload,
                request_id=response.request_id,
                retry_after=response.retry_after,
                latency_ms=latency_ms,
            )
        return response, latency_ms

    @staticmethod
    def _decode_json(response: HttpResponse, payload: dict[str, object], latency_ms: float) -> dict[str, object]:
        try:
            parsed = json.loads(
                response.body,
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
                object_pairs_hook=_reject_duplicate_json_keys,
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ModelProviderFailure(
                "malformed_response",
                "provider_returned_invalid_json",
                status_code=response.status_code,
                raw_response=response.body,
                request_payload=payload,
                request_id=response.request_id,
                latency_ms=latency_ms,
            ) from exc
        if not isinstance(parsed, dict):
            raise ModelProviderFailure(
                "malformed_response",
                "provider_response_not_object",
                status_code=response.status_code,
                raw_response=response.body,
                request_payload=payload,
                request_id=response.request_id,
                latency_ms=latency_ms,
            )
        return parsed


class OpenAIChatCompletionsAdapter(_BaseAdapter):
    """Adapter for OpenAI's Chat Completions endpoint with strict function tools."""

    def complete(self, messages: tuple[ResearchMessage, ...], tools: tuple[ToolDefinition, ...]) -> ModelTurn:
        api_key = self._credential()
        payload: dict[str, object] = {
            "model": self.config.model_id,
            "messages": [_openai_message(message) for message in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            "n": 1,
            "parallel_tool_calls": False,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                        "strict": True,
                    },
                }
                for tool in tools
            ],
            "tool_choice": "auto",
        }
        if self.config.seed is not None:
            payload["seed"] = self.config.seed
        if self.config.temperature is None:
            payload.pop("temperature")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response, latency_ms = self._request(payload, headers)
        parsed = self._decode_json(response, payload, latency_ms)
        try:
            choice = parsed["choices"][0]
            message = choice["message"]
            finish_reason = choice.get("finish_reason")
            content = message.get("content")
            text = content if isinstance(content, str) else None
            raw_calls = message.get("tool_calls") or []
            if not isinstance(raw_calls, list):
                raise TypeError
            calls = tuple(_parse_openai_tool_call(item) for item in raw_calls)
            usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else {}
            return ModelTurn(
                provider=self.config.provider,
                configured_model_id=self.config.model_id,
                observed_model_id=parsed.get("model") if isinstance(parsed.get("model"), str) else None,
                response_id=parsed.get("id") if isinstance(parsed.get("id"), str) else None,
                request_id=response.request_id,
                request_payload=payload,
                raw_response=response.body,
                latency_ms=latency_ms,
                input_tokens=_optional_int(usage.get("prompt_tokens")),
                output_tokens=_optional_int(usage.get("completion_tokens")),
                text=text,
                tool_calls=calls,
                finish_reason=finish_reason if isinstance(finish_reason, str) else None,
                refused=bool(message.get("refusal")) or finish_reason == "content_filter",
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelProviderFailure(
                "malformed_response",
                "openai_response_shape_invalid",
                status_code=response.status_code,
                raw_response=response.body,
                request_payload=payload,
                request_id=response.request_id,
                latency_ms=latency_ms,
            ) from exc


class AnthropicMessagesAdapter(_BaseAdapter):
    """Adapter for Anthropic Messages with client-side tools and input schemas."""

    def complete(self, messages: tuple[ResearchMessage, ...], tools: tuple[ToolDefinition, ...]) -> ModelTurn:
        api_key = self._credential()
        system, api_messages = _anthropic_messages(messages)
        payload: dict[str, object] = {
            "model": self.config.model_id,
            "max_tokens": self.config.max_output_tokens,
            "messages": api_messages,
            "tools": [
                {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
                for tool in tools
            ],
            "tool_choice": {"type": "auto"},
        }
        if system:
            payload["system"] = system
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }
        response, latency_ms = self._request(payload, headers)
        parsed = self._decode_json(response, payload, latency_ms)
        try:
            blocks = parsed["content"]
            if not isinstance(blocks, list):
                raise TypeError
            text_parts: list[str] = []
            tool_calls: list[ResearchToolCall] = []
            for block in blocks:
                if not isinstance(block, dict):
                    raise TypeError
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    text_parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tool_calls.append(_parse_anthropic_tool_call(block))
            usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else {}
            stop_reason = parsed.get("stop_reason")
            text = "\n".join(text_parts) or None
            return ModelTurn(
                provider=self.config.provider,
                configured_model_id=self.config.model_id,
                observed_model_id=parsed.get("model") if isinstance(parsed.get("model"), str) else None,
                response_id=parsed.get("id") if isinstance(parsed.get("id"), str) else None,
                request_id=response.request_id,
                request_payload=payload,
                raw_response=response.body,
                latency_ms=latency_ms,
                input_tokens=_optional_int(usage.get("input_tokens")),
                output_tokens=_optional_int(usage.get("output_tokens")),
                text=text,
                tool_calls=tuple(tool_calls),
                finish_reason=stop_reason if isinstance(stop_reason, str) else None,
                refused=stop_reason == "refusal",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelProviderFailure(
                "malformed_response",
                "anthropic_response_shape_invalid",
                status_code=response.status_code,
                raw_response=response.body,
                request_payload=payload,
                request_id=response.request_id,
                latency_ms=latency_ms,
            ) from exc


def _http_post_json(endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
    request = Request(endpoint, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return HttpResponse(
                response.status,
                response.read(),
                request_id=response.headers.get("x-request-id") or response.headers.get("request-id"),
                retry_after=response.headers.get("retry-after"),
            )
    except HTTPError as exc:
        return HttpResponse(
            exc.code,
            exc.read(),
            request_id=exc.headers.get("x-request-id") or exc.headers.get("request-id"),
            retry_after=exc.headers.get("retry-after"),
        )


def _openai_message(message: ResearchMessage) -> dict[str, object]:
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "name": message.name,
            "content": message.content or "",
        }
    if message.role == "assistant" and message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.call_id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": call.arguments_raw if call.arguments_raw is not None else _canonical_json(call.arguments or {}),
                    },
                }
                for call in message.tool_calls
            ],
        }
    return {"role": message.role, "content": message.content or ""}


def _anthropic_messages(messages: tuple[ResearchMessage, ...]) -> tuple[str, list[dict[str, object]]]:
    system_parts = [message.content or "" for message in messages if message.role == "system"]
    converted: list[dict[str, object]] = []
    for message in messages:
        if message.role == "system":
            continue
        if message.role == "assistant" and message.tool_calls:
            blocks: list[dict[str, object]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            blocks.extend({"type": "tool_use", "id": call.call_id, "name": call.name, "input": call.arguments or {}} for call in message.tool_calls)
            converted.append({"role": "assistant", "content": blocks})
        elif message.role == "tool":
            result = {
                "type": "tool_result",
                "tool_use_id": message.tool_call_id,
                "content": message.content or "",
            }
            if message.is_error:
                result["is_error"] = True
            if converted and converted[-1].get("role") == "user" and isinstance(converted[-1].get("content"), list):
                converted[-1]["content"].append(result)
            else:
                converted.append({"role": "user", "content": [result]})
        else:
            converted.append({"role": message.role, "content": message.content or ""})
    return "\n\n".join(part for part in system_parts if part), converted


def _parse_openai_tool_call(payload: object) -> ResearchToolCall:
    if not isinstance(payload, dict) or not isinstance(payload.get("function"), dict):
        raise TypeError("Tool call is not an object.")
    function = payload["function"]
    call_id = payload.get("id")
    name = function.get("name")
    raw = function.get("arguments")
    if not isinstance(call_id, str) or not isinstance(name, str) or not isinstance(raw, str):
        raise TypeError("Tool call identifiers or arguments are missing.")
    try:
        arguments = json.loads(
            raw,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (json.JSONDecodeError, ValueError):
        return ResearchToolCall(call_id, name, None, raw, "invalid_json")
    if not isinstance(arguments, dict):
        return ResearchToolCall(call_id, name, None, raw, "arguments_not_object")
    return ResearchToolCall(call_id, name, arguments, raw)


def _parse_anthropic_tool_call(payload: dict[str, object]) -> ResearchToolCall:
    call_id = payload.get("id")
    name = payload.get("name")
    arguments = payload.get("input")
    if not isinstance(call_id, str) or not isinstance(name, str):
        raise TypeError("Tool call identifiers are missing.")
    if not isinstance(arguments, dict):
        return ResearchToolCall(call_id, name, None, _canonical_json({}), "arguments_not_object")
    return ResearchToolCall(call_id, name, arguments, _canonical_json(arguments))


def _optional_int(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKeyError(key)
        result[key] = value
    return result
