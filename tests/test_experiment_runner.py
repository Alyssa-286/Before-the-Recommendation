from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from before_recommendation import experiment_runner
from before_recommendation.config import load_phase1_config
from before_recommendation.experiment_runner import ModelBatchRunner, plan_trials
from before_recommendation.leakage import check_request_payload
from before_recommendation.live_controller import LIVE_SYSTEM_INSTRUCTION, _public_catalog_payload
from before_recommendation.conditions import MarketingCondition, generate_cue_arms
from before_recommendation.model_adapters import HttpResponse, ModelConfig
from before_recommendation.scenarios import generate_scenarios


def _chat(call_id: str, name: str, arguments: dict) -> HttpResponse:
    body = {
        "id": f"resp-{call_id}",
        "model": "fake-model",
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}
            ]},
        }],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }
    return HttpResponse(200, json.dumps(body).encode(), request_id=None)


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = generate_scenarios(load_phase1_config())
        cls.config = ModelConfig("openai_chat_completions", "fake-model", "fake_family", "UNIT_TEST_RUNNER_KEY", temperature=None)
        cls.output = {
            "preference_weights": {"price": 0.4, "quality": 0.3, "durability": 0.2, "sustainability": 0.1},
            "ranked_products": [p.product_id for p in cls.scenarios[0].catalog.products],
            "evidence_used": ["price_inr"],
            "uncertainty": 0.3,
            "final_explanation": "Balanced choice.",
        }

    def _planned(self):
        return plan_trials(self.config, self.scenarios[:1], ("ambiguous",), ("neutral",), (1,), "unit-test", "abcdef0")

    def test_transient_status_is_resent_and_logged_without_trial_failure(self) -> None:
        responses = [
            HttpResponse(503, b'{"error":"overloaded"}', request_id=None),
            _chat("c1", "inspect_catalog", {}),
            _chat("c2", "submit_recommendation", self.output),
        ]
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.dict(os.environ, {"UNIT_TEST_RUNNER_KEY": "unit-secret"}), \
                mock.patch.object(experiment_runner, "_http_post_json", side_effect=lambda *a: responses.pop(0)), \
                mock.patch.object(experiment_runner.time, "sleep"):
            runner = ModelBatchRunner(Path(temp), self.config, self._planned(), min_interval_seconds=0)
            status = runner.run()
            self.assertEqual(status["status_counts"], {"completed": 1})
            events = (runner.run_dir / "transport_events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 1)
            self.assertEqual(json.loads(events[0])["status_code"], 503)
            self.assertNotIn("unit-secret", (runner.run_dir / "model_io.attempt1.jsonl").read_text(encoding="utf-8"))

    def test_provider_failure_gets_exactly_one_preserved_technical_retry(self) -> None:
        responses = [HttpResponse(400, b'{"error":"bad"}', request_id=None), HttpResponse(400, b'{"error":"bad"}', request_id=None)]
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.dict(os.environ, {"UNIT_TEST_RUNNER_KEY": "unit-secret"}), \
                mock.patch.object(experiment_runner, "_http_post_json", side_effect=lambda *a: responses.pop(0)):
            runner = ModelBatchRunner(Path(temp), self.config, self._planned(), min_interval_seconds=0)
            status = runner.run()
            self.assertEqual(status["status_counts"], {"failed": 1})
            self.assertTrue((runner.run_dir / "traces.attempt1.jsonl").exists())
            self.assertTrue((runner.run_dir / "traces.attempt2.jsonl").exists())
            events = [json.loads(line) for line in (runner.run_dir / "runner_events.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([e["record_type"] for e in events], ["trial_attempt_finished", "technical_retry_scheduled", "trial_attempt_finished"])

    def test_protocol_violation_is_not_retried(self) -> None:
        responses = [_chat("c1", "submit_recommendation", self.output)]
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.dict(os.environ, {"UNIT_TEST_RUNNER_KEY": "unit-secret"}), \
                mock.patch.object(experiment_runner, "_http_post_json", side_effect=lambda *a: responses.pop(0)):
            runner = ModelBatchRunner(Path(temp), self.config, self._planned(), min_interval_seconds=0)
            runner.run()
            self.assertFalse((runner.run_dir / "traces.attempt2.jsonl").exists())


class LeakageTests(unittest.TestCase):
    def test_model_visible_payload_is_clean_and_injected_truth_is_detected(self) -> None:
        scenario = generate_scenarios(load_phase1_config())[0]
        arm = next(a for a in generate_cue_arms(scenario.catalog, scenario.config) if a.condition is MarketingCondition.DISCOUNT)
        catalog = _public_catalog_payload(arm.listings, MarketingCondition.DISCOUNT, scenario.catalog)
        clean = {"messages": [
            {"role": "system", "content": LIVE_SYSTEM_INSTRUCTION},
            {"role": "user", "content": "I need a good laptop for college."},
            {"role": "tool", "content": json.dumps(catalog)},
        ]}
        self.assertEqual(check_request_payload(clean, scenario), [])
        weight = dict(scenario.objective.weights)["price"]
        dirty = {"messages": clean["messages"] + [{"role": "user", "content": f"optimal weight {weight!r}"}]}
        findings = check_request_payload(dirty, scenario)
        self.assertIn("term:optimal", findings)
        self.assertIn("weight_value:price", findings)


if __name__ == "__main__":
    unittest.main()
