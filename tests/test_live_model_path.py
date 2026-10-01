from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from before_recommendation.checkpoint import CheckpointStore, TrialStatus
from before_recommendation.analysis import build_trial_rows
from before_recommendation.config import load_phase1_config
from before_recommendation.failures import FailureCategory, JsonlFailureLogger
from before_recommendation.live_controller import (
    LIVE_TOOLS,
    LiveTrialController,
    RawModelIOLogger,
    live_trial_config_sha256,
)
from before_recommendation.live_output import LIVE_OUTPUT_SCHEMA_VERSION, parse_live_output
from before_recommendation.model_adapters import (
    AnthropicMessagesAdapter,
    GeminiOpenAICompatAdapter,
    HttpResponse,
    GroqChatCompletionsAdapter,
    ModelConfig,
    ModelProviderFailure,
    ModelTurn,
    OpenAIChatCompletionsAdapter,
    ResearchMessage,
    ResearchToolCall,
    ToolDefinition,
    make_adapter,
)
from before_recommendation.prompts import GoalCondition
from before_recommendation.scenarios import generate_scenarios
from before_recommendation.simulated_user import UNCERTAINTY_ANSWER, answer_clarification
from before_recommendation.tracing import JsonlTraceLogger, TrialIdentity


def _tool_call(call_id: str, name: str, value: object, raw: str | None = None) -> ResearchToolCall:
    return ResearchToolCall(call_id, name, value if isinstance(value, dict) else None, raw or json.dumps(value, separators=(",", ":")))


def _turn(model_id: str, call: ResearchToolCall | tuple[ResearchToolCall, ...], *, text: str | None = None) -> ModelTurn:
    calls = call if isinstance(call, tuple) else (call,)
    return ModelTurn(
        provider="openai_chat_completions",
        configured_model_id=model_id,
        observed_model_id=model_id,
        response_id=f"resp-{calls[0].call_id}",
        request_id=f"req-{calls[0].call_id}",
        request_payload={"model": model_id},
        raw_response=json.dumps({"id": f"resp-{calls[0].call_id}", "tool_calls": [call.call_id for call in calls]}).encode(),
        latency_ms=1.25,
        input_tokens=10,
        output_tokens=8,
        text=text,
        tool_calls=calls,
        finish_reason="tool_calls",
        refused=False,
    )


class ScriptedAdapter:
    def __init__(self, turns: list[ModelTurn], model_id: str = "mock-live-v1") -> None:
        self.config = ModelConfig("openai_chat_completions", model_id, "test_family", "NEVER_SET_RESEARCH_KEY")
        self.turns = list(turns)
        self.seen_messages: list[tuple[ResearchMessage, ...]] = []

    def complete(self, messages: tuple[ResearchMessage, ...], tools: tuple[ToolDefinition, ...]) -> ModelTurn:
        self.seen_messages.append(messages)
        if tools != LIVE_TOOLS:
            raise AssertionError("Unexpected model tool contract.")
        return self.turns.pop(0)


class LiveOutputParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ids = ("LumaBook_P01", "LumaBook_P02")

    def test_accepts_model_owned_fields_only(self) -> None:
        raw = json.dumps({
            "preference_weights": {"price": 0.4, "quality": 0.3, "durability": 0.2, "sustainability": 0.1},
            "ranked_products": [self.ids[0], self.ids[1]],
            "evidence_used": ["price_inr", "quality"],
            "uncertainty": 0.2,
            "final_explanation": "This option fits the stated priorities.",
        })
        parsed = parse_live_output(raw, self.ids)
        self.assertTrue(parsed.valid)
        self.assertEqual(parsed.schema_version, LIVE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(parsed.raw_output, raw)

    def test_rejects_controller_fields_duplicates_unknown_products_and_bad_weights(self) -> None:
        payload = {
            "preference_weights": {"price": 0.7, "quality": 0.3, "durability": 0.2, "sustainability": 0.1},
            "ranked_products": ["UNKNOWN"],
            "evidence_used": [],
            "uncertainty": 0.2,
            "final_explanation": "Reason.",
            "simulated_user_answer": "must not be model-owned",
        }
        parsed = parse_live_output(json.dumps(payload), self.ids)
        codes = {issue.code for issue in parsed.errors}
        self.assertFalse(parsed.valid)
        self.assertIn("additional_property", codes)
        self.assertIn("unknown_product", codes)
        self.assertIn("sum", codes)
        duplicate = parse_live_output('{"x":1,"x":2}', self.ids)
        self.assertEqual(duplicate.status.value, "invalid_json")


class ProviderAdapterTests(unittest.TestCase):
    def test_live_config_hash_is_stable_and_setting_sensitive(self) -> None:
        first = ModelConfig("openai_chat_completions", "model-a", "family-a", "KEY_ENV", temperature=0.0, seed=3)
        same = ModelConfig("openai_chat_completions", "model-a", "family-a", "KEY_ENV", temperature=0.0, seed=3)
        changed = ModelConfig("openai_chat_completions", "model-a", "family-a", "KEY_ENV", temperature=0.2, seed=3)
        digest = live_trial_config_sha256(first, "b" * 64, "phase2-test-v1")
        self.assertEqual(digest, live_trial_config_sha256(same, "b" * 64, "phase2-test-v1"))
        self.assertNotEqual(digest, live_trial_config_sha256(changed, "b" * 64, "phase2-test-v1"))

    def test_credential_configuration_accepts_only_an_environment_variable_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "environment-variable name"):
            ModelConfig("openai_chat_completions", "model-a", "family-a", "sk-this-must-never-be-a-value")

    def test_openai_request_is_strict_and_does_not_return_secret(self) -> None:
        secret = "unit-test-secret-openai"
        captured: dict[str, object] = {}

        def transport(endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
            captured.update(endpoint=endpoint, headers=headers, body=json.loads(body), timeout=timeout)
            return HttpResponse(200, json.dumps({
                "id": "x", "model": "openai-test", "choices": [{
                    "finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [{
                        "id": "call-1", "type": "function", "function": {"name": "inspect_catalog", "arguments": "{}"}
                    }]}
                }], "usage": {"prompt_tokens": 4, "completion_tokens": 2}
            }).encode(), "rid-1")

        config = ModelConfig("openai_chat_completions", "openai-test", "family-a", "UNIT_TEST_OPENAI_KEY", seed=21)
        with patch.dict(os.environ, {"UNIT_TEST_OPENAI_KEY": secret}):
            turn = OpenAIChatCompletionsAdapter(config, transport).complete(
                (ResearchMessage("system", "protocol"), ResearchMessage("user", "request")),
                LIVE_TOOLS,
            )
        self.assertEqual(captured["headers"]["Authorization"], f"Bearer {secret}")
        self.assertTrue(captured["body"]["tools"][0]["function"]["strict"])
        self.assertFalse(captured["body"]["parallel_tool_calls"])
        self.assertEqual(captured["body"]["seed"], 21)
        serialized_schema = json.dumps(captured["body"]["tools"])
        self.assertNotIn("uniqueItems", serialized_schema)
        self.assertNotIn("minLength", serialized_schema)
        self.assertEqual(turn.tool_calls[0].name, "inspect_catalog")
        self.assertNotIn(secret, repr(turn))
        self.assertNotIn(secret, repr(config.public_dict()))

    def test_gemini_openai_compat_tool_calls_preserve_google_turn_metadata(self) -> None:
        secret = "unit-test-gemini-secret"
        captured: list[dict[str, object]] = []
        responses = [
            {
                "id": "gemini-response-1", "model": "gemini-test", "choices": [{
                    "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [{
                        "id": "gemini-call-1", "type": "function",
                        "function": {"name": "inspect_catalog", "arguments": "{}"},
                        "extra_content": {"google": {"thought_signature": "opaque-test-signature"}},
                    }]}
                }], "usage": {"prompt_tokens": 6, "completion_tokens": 3},
            },
            {
                "id": "gemini-response-2", "model": "gemini-test", "choices": [{
                    "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [{
                        "id": "gemini-call-2", "type": "function",
                        "function": {"name": "submit_recommendation", "arguments": "{}"},
                    }]}
                }], "usage": {"prompt_tokens": 9, "completion_tokens": 4},
            },
        ]

        def transport(endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
            captured.append({"endpoint": endpoint, "headers": headers, "body": json.loads(body)})
            return HttpResponse(200, json.dumps(responses.pop(0)).encode(), f"gemini-rid-{len(captured)}")

        config = ModelConfig("gemini_openai_compat", "gemini-test", "google_gemini", "UNIT_TEST_GEMINI_KEY")
        adapter = make_adapter(config, transport)
        self.assertIsInstance(adapter, GeminiOpenAICompatAdapter)
        with patch.dict(os.environ, {"UNIT_TEST_GEMINI_KEY": secret}):
            first = adapter.complete((ResearchMessage("system", "protocol"), ResearchMessage("user", "request")), LIVE_TOOLS)
            second = adapter.complete((
                ResearchMessage("system", "protocol"),
                ResearchMessage("user", "request"),
                ResearchMessage("assistant", tool_calls=first.tool_calls, provider_metadata=first.provider_metadata),
                ResearchMessage("tool", "catalog facts", tool_call_id=first.tool_calls[0].call_id, name="inspect_catalog"),
            ), LIVE_TOOLS)
        first_payload = captured[0]["body"]
        self.assertEqual(captured[0]["endpoint"], "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        self.assertEqual(captured[0]["headers"]["Authorization"], f"Bearer {secret}")
        self.assertNotIn("strict", first_payload["tools"][0]["function"])
        self.assertEqual(first.tool_calls[0].name, "inspect_catalog")
        self.assertEqual(first.tool_calls[0].provider_metadata["extra_content"]["google"]["thought_signature"], "opaque-test-signature")
        returned_call = captured[1]["body"]["messages"][2]["tool_calls"][0]
        self.assertEqual(returned_call["extra_content"]["google"]["thought_signature"], "opaque-test-signature")
        self.assertEqual(first.raw_response, json.dumps({
            "id": "gemini-response-1", "model": "gemini-test", "choices": [{
                "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "gemini-call-1", "type": "function",
                    "function": {"name": "inspect_catalog", "arguments": "{}"},
                    "extra_content": {"google": {"thought_signature": "opaque-test-signature"}},
                }]}
            }], "usage": {"prompt_tokens": 6, "completion_tokens": 3},
        }).encode())
        self.assertEqual((first.input_tokens, first.output_tokens), (6, 3))
        self.assertEqual(second.observed_model_id, "gemini-test")
        self.assertNotIn(secret, repr(first))

    def test_groq_uses_documented_completion_limit_and_maps_rate_limit_safely(self) -> None:
        secret = "unit-test-groq-secret"
        captured: dict[str, object] = {}

        def transport(endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
            captured.update(endpoint=endpoint, headers=headers, body=json.loads(body))
            return HttpResponse(200, json.dumps({
                "id": "groq-response", "model": "groq-test", "choices": [{
                    "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [{
                        "id": "groq-call", "type": "function", "function": {"name": "inspect_catalog", "arguments": "{}"}
                    }]}
                }], "usage": {"prompt_tokens": 8, "completion_tokens": 2},
            }).encode(), "groq-rid")

        config = ModelConfig("groq_chat_completions", "groq-test", "groq-test-family", "UNIT_TEST_GROQ_KEY", seed=7)
        adapter = make_adapter(config, transport)
        self.assertIsInstance(adapter, GroqChatCompletionsAdapter)
        with patch.dict(os.environ, {"UNIT_TEST_GROQ_KEY": secret}):
            turn = adapter.complete((ResearchMessage("user", "request"),), LIVE_TOOLS)
        self.assertEqual(captured["endpoint"], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], f"Bearer {secret}")
        self.assertEqual(captured["body"]["max_completion_tokens"], 1200)
        self.assertEqual(captured["body"]["seed"], 7)
        self.assertFalse(captured["body"]["parallel_tool_calls"])
        self.assertNotIn("strict", captured["body"]["tools"][0]["function"])
        self.assertEqual(turn.tool_calls[0].name, "inspect_catalog")
        self.assertEqual(turn.raw_response, json.dumps({
            "id": "groq-response", "model": "groq-test", "choices": [{
                "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "groq-call", "type": "function", "function": {"name": "inspect_catalog", "arguments": "{}"}
                }]}
            }], "usage": {"prompt_tokens": 8, "completion_tokens": 2},
        }).encode())
        self.assertEqual((turn.input_tokens, turn.output_tokens), (8, 2))
        self.assertEqual(turn.request_id, "groq-rid")

        error_bytes = f'{{"error":{{"message":"{secret}"}}}}'.encode()
        with patch.dict(os.environ, {"UNIT_TEST_GROQ_KEY": secret}):
            with self.assertRaises(ModelProviderFailure) as raised:
                GroqChatCompletionsAdapter(config, lambda *args: HttpResponse(429, error_bytes, "limited", "4")).complete(
                    (ResearchMessage("user", "request"),), LIVE_TOOLS
                )
        self.assertEqual(raised.exception.category, "rate_limit")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.request_id, "limited")
        self.assertEqual(raised.exception.retry_after, "4")
        self.assertNotIn(secret.encode(), raised.exception.raw_response)
        self.assertIn(b"[REDACTED]", raised.exception.raw_response)
        self.assertNotIn(secret, str(raised.exception))

    def test_anthropic_maps_tool_result_and_tool_use(self) -> None:
        secret = "unit-test-secret-anthropic"
        captured: dict[str, object] = {}

        def transport(endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
            captured.update(headers=headers, body=json.loads(body))
            return HttpResponse(200, json.dumps({
                "id": "msg-1", "model": "anthropic-test", "stop_reason": "tool_use",
                "content": [{"type": "tool_use", "id": "call-2", "name": "inspect_catalog", "input": {}}],
                "usage": {"input_tokens": 5, "output_tokens": 3},
            }).encode())

        config = ModelConfig("anthropic_messages", "anthropic-test", "family-b", "UNIT_TEST_ANTHROPIC_KEY")
        messages = (
            ResearchMessage("system", "system text"),
            ResearchMessage("user", "request"),
            ResearchMessage("assistant", tool_calls=(_tool_call("c0", "ask_clarification", {"question": "Price?", "target": "price"}),)),
            ResearchMessage("tool", "Price matters most.", tool_call_id="c0", name="ask_clarification"),
        )
        with patch.dict(os.environ, {"UNIT_TEST_ANTHROPIC_KEY": secret}):
            turn = AnthropicMessagesAdapter(config, transport).complete(messages, (LIVE_TOOLS[0],))
        self.assertEqual(captured["headers"]["x-api-key"], secret)
        self.assertEqual(captured["body"]["system"], "system text")
        self.assertEqual(captured["body"]["messages"][-1]["content"][0]["content"], "Price matters most.")
        self.assertEqual(turn.tool_calls[0].name, "inspect_catalog")
        self.assertNotIn(secret, repr(turn))

    def test_missing_credentials_fail_before_network(self) -> None:
        calls = []

        def transport(*args: object) -> HttpResponse:
            calls.append(args)
            return HttpResponse(200, b"{}")

        config = ModelConfig("openai_chat_completions", "m", "f", "ABSENT_UNIT_TEST_KEY")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ModelProviderFailure) as raised:
                OpenAIChatCompletionsAdapter(config, transport).complete((ResearchMessage("user", "hi"),), ())
        self.assertEqual(raised.exception.detail_code, "missing_credential")
        self.assertEqual(calls, [])

    def test_openai_duplicate_tool_argument_keys_are_rejected(self) -> None:
        def transport(*args: object) -> HttpResponse:
            return HttpResponse(200, json.dumps({
                "choices": [{"message": {"tool_calls": [{
                    "id": "duplicate", "function": {"name": "ask_clarification", "arguments": '{"question":"Price?","target":"price","target":"quality"}'}
                }]}}]
            }).encode())

        config = ModelConfig("openai_chat_completions", "m", "f", "UNIT_TEST_DUPLICATE_KEY")
        with patch.dict(os.environ, {"UNIT_TEST_DUPLICATE_KEY": "test-only"}):
            turn = OpenAIChatCompletionsAdapter(config, transport).complete((ResearchMessage("user", "hi"),), ())
        self.assertEqual(turn.tool_calls[0].argument_error, "invalid_json")

    def test_http_rate_limit_preserves_provider_error_bytes(self) -> None:
        raw_error = b'{"error":{"type":"rate_limit","message":"slow down"}}'

        def transport(*args: object) -> HttpResponse:
            return HttpResponse(429, raw_error, "request-429", "2")

        config = ModelConfig("openai_chat_completions", "openai-test", "family-a", "UNIT_TEST_HTTP_KEY")
        with patch.dict(os.environ, {"UNIT_TEST_HTTP_KEY": "secret-value"}):
            with self.assertRaises(ModelProviderFailure) as raised:
                OpenAIChatCompletionsAdapter(config, transport).complete((ResearchMessage("user", "hi"),), ())
        self.assertEqual(raised.exception.category, "rate_limit")
        self.assertEqual(raised.exception.raw_response, raw_error)
        self.assertEqual(raised.exception.request_id, "request-429")
        self.assertEqual(raised.exception.retry_after, "2")


class LiveControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_phase1_config()
        cls.scenario = generate_scenarios(cls.config)[0]
        cls.model_id = "mock-live-v1"
        cls.output = {
            "preference_weights": {"price": 0.4, "quality": 0.3, "durability": 0.2, "sustainability": 0.1},
            "ranked_products": [product.product_id for product in cls.scenario.catalog.products],
            "evidence_used": ["price_inr", "quality"],
            "uncertainty": 0.2,
            "final_explanation": "The first listing balances the stated factors.",
        }

    def _identity(
        self,
        scenario=None,
        model_config: ModelConfig | None = None,
        marketing_condition: str = "neutral",
    ) -> TrialIdentity:
        selected_scenario = scenario or self.scenario
        selected_model = model_config or ModelConfig(
            "openai_chat_completions", self.model_id, "test_family", "NEVER_SET_RESEARCH_KEY"
        )
        experiment_version = "test-v1"
        return TrialIdentity(
            scenario_id=selected_scenario.scenario_id,
            profile_id=selected_scenario.objective.objective_id,
            goal_condition=GoalCondition.AMBIGUOUS.value,
            marketing_condition=marketing_condition,
            model_family="test_family",
            model_version=self.model_id,
            repetition=1,
            prompt_template_id="ambiguous-v1-01",
            experiment_version=experiment_version,
            config_sha256=live_trial_config_sha256(selected_model, selected_scenario.config.config_sha256, experiment_version),
            random_seed=1,
            code_revision="abcdef0",
        )

    def _execute(self, adapter: ScriptedAdapter, identity: TrialIdentity | None = None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        current_identity = identity or self._identity(model_config=adapter.config)
        checkpoint = CheckpointStore(root / "checkpoint.sqlite", current_identity.config_sha256)
        checkpoint.register_trials((current_identity,))
        traces = JsonlTraceLogger(root / "traces.jsonl")
        raw = RawModelIOLogger(root / "model_io.jsonl")
        failures = JsonlFailureLogger(root / "failures.jsonl")
        runner = LiveTrialController(adapter, checkpoint, traces, raw, failures)
        result = runner.run(current_identity, self.scenario)
        return result, checkpoint, root

    def test_inspection_then_controller_answer_then_final_output(self) -> None:
        adapter = ScriptedAdapter([
            _turn(self.model_id, _tool_call("c1", "inspect_catalog", {})),
            _turn(self.model_id, _tool_call("c2", "ask_clarification", {"question": "How important is price?", "target": "price"})),
            _turn(self.model_id, _tool_call("c3", "submit_recommendation", self.output)),
        ])
        result, checkpoint, root = self._execute(adapter)
        self.assertTrue(result.completed)
        self.assertEqual(checkpoint.get(result.trace.identity.trial_id).status, TrialStatus.COMPLETED)
        self.assertEqual(result.trace.agent_visible_input.catalog_listings, ())
        self.assertEqual(len(result.trace.attempts), 1)
        self.assertEqual(result.trace.attempts[0].result.schema_version, "2.0.0")
        self.assertEqual(adapter.seen_messages[0][-1].content, "I need a good laptop for college. I want something affordable, reliable and reasonably sustainable.")
        visible_catalog_json = adapter.seen_messages[1][-1].content
        self.assertIn("LumaBook_P01", visible_catalog_json)
        self.assertNotIn(self.scenario.objective.objective_id, visible_catalog_json)
        self.assertNotIn("objective", visible_catalog_json)
        answer = adapter.seen_messages[2][-1].content
        self.assertEqual(answer, answer_clarification(self.scenario.objective, "price").answer)
        self.assertNotIn("simulated_user_answer", result.trace.attempts[0].result.data)
        self.assertTrue(result.trace.evaluator_private["factual_utility_balance"]["balanced"])
        self.assertEqual(result.trace.evaluator_private["factual_utility_balance"]["max_per_product_utility_difference"], 0.0)
        analysis_row = build_trial_rows((result.trace.as_dict(),))[0]
        self.assertTrue(analysis_row["is_valid"])
        self.assertTrue(analysis_row["clarification_needed"])
        self.assertEqual(analysis_row["output_schema_version"], "2.0.0")
        self.assertEqual(analysis_row["top_recommended_product_id"], self.scenario.catalog.products[0].product_id)
        model_io = (root / "model_io.jsonl").read_text(encoding="utf-8")
        self.assertEqual(model_io.count('"record_type":"model_io"'), 3)
        self.assertIn('"headers_logged":false', model_io)
        self.assertEqual(tuple(event.sequence for event in result.trace.events), tuple(range(len(result.trace.events))))
        self.assertEqual(len(result.trace.events), 12)

    def test_compound_question_gets_standardized_uncertainty_answer(self) -> None:
        adapter = ScriptedAdapter([
            _turn(self.model_id, _tool_call("c1", "inspect_catalog", {})),
            _turn(self.model_id, _tool_call("c2", "ask_clarification", {"question": "Which matters more, price or quality?", "target": "price"})),
            _turn(self.model_id, _tool_call("c3", "submit_recommendation", self.output)),
        ])
        result, _, _ = self._execute(adapter)
        self.assertTrue(result.completed)
        self.assertEqual(adapter.seen_messages[2][-1].content, UNCERTAINTY_ANSWER)
        inserted = next(event for event in result.trace.events if event.event_type == "simulated_user_answer")
        self.assertFalse(inserted.payload["supported"])

    def test_cue_condition_changes_labels_but_not_factual_catalog(self) -> None:
        neutral_adapter = ScriptedAdapter([
            _turn(self.model_id, _tool_call("n1", "inspect_catalog", {})),
            _turn(self.model_id, _tool_call("n2", "submit_recommendation", self.output)),
        ])
        scarcity_adapter = ScriptedAdapter([
            _turn(self.model_id, _tool_call("s1", "inspect_catalog", {})),
            _turn(self.model_id, _tool_call("s2", "submit_recommendation", self.output)),
        ])
        neutral, _, _ = self._execute(neutral_adapter, self._identity(marketing_condition="neutral"))
        scarcity, _, _ = self._execute(scarcity_adapter, self._identity(marketing_condition="scarcity"))
        def parse(text: str) -> list[dict[str, str]]:
            lines = text.splitlines()
            header = lines[1].split("|")
            return [dict(zip(header, line.split("|"))) for line in lines[2:]]

        neutral_text = neutral_adapter.seen_messages[1][-1].content
        scarcity_text = scarcity_adapter.seen_messages[1][-1].content
        neutral_rows, scarcity_rows = parse(neutral_text), parse(scarcity_text)
        self.assertTrue(neutral.completed and scarcity.completed)
        # The model never sees the experimental arm name, only the listing labels.
        self.assertNotIn("scarcity", scarcity_text.casefold())
        self.assertNotIn("neutral", neutral_text.casefold())
        self.assertEqual(len(neutral_rows), 20)
        self.assertEqual(
            [{key: value for key, value in row.items() if key != "marketing_label"} for row in neutral_rows],
            [{key: value for key, value in row.items() if key != "marketing_label"} for row in scarcity_rows],
        )
        self.assertTrue(all(row["marketing_label"] == "-" for row in neutral_rows))
        self.assertEqual(sum(row["marketing_label"] != "-" for row in scarcity_rows), 5)

    def test_clarification_before_inspection_is_preserved_as_failure(self) -> None:
        adapter = ScriptedAdapter([_turn(self.model_id, _tool_call("c1", "ask_clarification", {"question": "Price?", "target": "price"}))])
        result, checkpoint, root = self._execute(adapter)
        self.assertFalse(result.completed)
        self.assertEqual(result.failure.category, FailureCategory.CATALOG_INSPECTION_MISSING)
        self.assertEqual(checkpoint.get(result.trace.identity.trial_id).status, TrialStatus.FAILED)
        self.assertEqual([event.event_type for event in result.trace.events], ["trial_started", "response_received", "tool_call", "trial_failed"])
        self.assertTrue((root / "model_io.jsonl").exists())

    def test_parallel_tool_calls_are_not_repaired(self) -> None:
        calls = (
            _tool_call("c1", "inspect_catalog", {}),
            _tool_call("c2", "ask_clarification", {"question": "Price?", "target": "price"}),
        )
        adapter = ScriptedAdapter([_turn(self.model_id, calls)])
        result, _, _ = self._execute(adapter)
        self.assertFalse(result.completed)
        self.assertEqual(result.failure.detail_code, "expected_exactly_one_tool_call")
        self.assertFalse(any(event.event_type == "catalog_inspected" for event in result.trace.events))

    def test_one_invalid_recommendation_is_retained_before_valid_retry(self) -> None:
        invalid = dict(self.output)
        invalid["preference_weights"] = {"price": 0.9, "quality": 0.2, "durability": 0.2, "sustainability": 0.1}
        adapter = ScriptedAdapter([
            _turn(self.model_id, _tool_call("c1", "inspect_catalog", {})),
            _turn(self.model_id, _tool_call("c2", "submit_recommendation", invalid)),
            _turn(self.model_id, _tool_call("c3", "submit_recommendation", self.output)),
        ])
        result, _, _ = self._execute(adapter)
        self.assertTrue(result.completed)
        self.assertEqual(len(result.trace.attempts), 2)
        self.assertFalse(result.trace.attempts[0].result.valid)
        self.assertTrue(result.trace.attempts[1].result.valid)
        self.assertTrue(any(event.event_type == "parser_retry_requested" for event in result.trace.events))
        self.assertEqual(len(result.trace.failures), 1)
        self.assertTrue(result.trace.failures[0].recoverable)

    def test_second_clarification_is_a_preserved_failure(self) -> None:
        adapter = ScriptedAdapter([
            _turn(self.model_id, _tool_call("c1", "inspect_catalog", {})),
            _turn(self.model_id, _tool_call("c2", "ask_clarification", {"question": "Price?", "target": "price"})),
            _turn(self.model_id, _tool_call("c3", "ask_clarification", {"question": "Quality?", "target": "quality"})),
        ])
        result, _, _ = self._execute(adapter)
        self.assertFalse(result.completed)
        self.assertEqual(result.failure.detail_code, "more_than_one_clarification")
        self.assertEqual(sum(message.role == "tool" for message in adapter.seen_messages[-1]), 2)

    def test_provider_rate_limit_is_logged_and_fails_checkpoint(self) -> None:
        raw_error = b'{"error":{"type":"rate_limit","message":"rate limited"}}'

        def transport(*args: object) -> HttpResponse:
            return HttpResponse(429, raw_error, "rid-limit", "3")

        provider_config = ModelConfig("openai_chat_completions", self.model_id, "test_family", "LIVE_CONTROLLER_TEST_KEY")
        adapter = OpenAIChatCompletionsAdapter(provider_config, transport)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        identity = self._identity(model_config=provider_config)
        checkpoint = CheckpointStore(root / "checkpoint.sqlite", identity.config_sha256)
        checkpoint.register_trials((identity,))
        runner = LiveTrialController(
            adapter, checkpoint, JsonlTraceLogger(root / "traces.jsonl"),
            RawModelIOLogger(root / "model_io.jsonl"), JsonlFailureLogger(root / "failures.jsonl"),
        )
        with patch.dict(os.environ, {"LIVE_CONTROLLER_TEST_KEY": "secret-value"}):
            result = runner.run(identity, self.scenario)
        self.assertFalse(result.completed)
        self.assertEqual(result.failure.category, FailureCategory.RATE_LIMIT)
        self.assertEqual(checkpoint.get(identity.trial_id).status, TrialStatus.FAILED)
        model_io = (root / "model_io.jsonl").read_text(encoding="utf-8")
        record = json.loads(model_io)
        self.assertEqual(base64.b64decode(record["raw_response_base64"]), raw_error)
        self.assertIn("rate limited", record["raw_response_text"])
        self.assertIn("rid-limit", model_io)
        self.assertIn('"headers_logged":false', model_io)
        self.assertNotIn("secret-value", model_io)


if __name__ == "__main__":
    unittest.main()
