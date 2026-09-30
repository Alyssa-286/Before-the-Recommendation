from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from before_recommendation.model_adapters import HttpResponse, ModelConfig, OpenAIChatCompletionsAdapter, ResearchMessage
from before_recommendation.runtime_config import load_runtime_environment


class RuntimeConfigTests(unittest.TestCase):
    def test_loads_only_requested_variables_without_overriding_process_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text(
                'RUNTIME_TEST_KEY="test-only-value"\nUNREQUESTED_TEST_KEY=not-loaded\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"RUNTIME_TEST_KEY": "process-value"}, clear=True):
                self.assertTrue(load_runtime_environment(dotenv_path, names=("RUNTIME_TEST_KEY", "UNREQUESTED_TEST_KEY")))
                self.assertEqual(os.environ["RUNTIME_TEST_KEY"], "process-value")
                self.assertEqual(os.environ["UNREQUESTED_TEST_KEY"], "not-loaded")
            with patch.dict(os.environ, {}, clear=True):
                self.assertTrue(load_runtime_environment(dotenv_path, names=("RUNTIME_TEST_KEY",)))
                self.assertEqual(os.environ["RUNTIME_TEST_KEY"], "test-only-value")
                self.assertNotIn("UNREQUESTED_TEST_KEY", os.environ)

    def test_missing_file_is_a_safe_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertFalse(load_runtime_environment(Path(temp_dir) / "absent.env", names=("ABSENT_KEY",)))

    def test_adapter_loads_project_local_env_before_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("LOCAL_DOTENV_TEST_KEY=synthetic-test-value\n", encoding="utf-8")
            seen: dict[str, object] = {}

            def transport(endpoint: str, headers: dict[str, str], body: bytes, timeout: float) -> HttpResponse:
                seen.update(endpoint=endpoint, headers=headers, body=json.loads(body))
                return HttpResponse(200, json.dumps({
                    "id": "dotenv-response", "model": "dotenv-test", "choices": [{
                        "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}
                    }], "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }).encode())

            config = ModelConfig("openai_chat_completions", "dotenv-test", "test-family", "LOCAL_DOTENV_TEST_KEY")
            with patch.dict(os.environ, {}, clear=True), patch("before_recommendation.runtime_config.PROJECT_ROOT", root):
                turn = OpenAIChatCompletionsAdapter(config, transport).complete((ResearchMessage("user", "request"),), ())
            self.assertEqual(seen["headers"]["Authorization"], "Bearer synthetic-test-value")
            self.assertEqual(turn.observed_model_id, "dotenv-test")
            self.assertNotIn("synthetic-test-value", repr(turn))
            self.assertNotIn("synthetic-test-value", repr(config.public_dict()))


if __name__ == "__main__":
    unittest.main()
