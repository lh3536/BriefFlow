"""Direct tests for backend/llm.py (payload construction, edge cases)."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from backend.llm import _config, _load_dotenv, chat_completion, llm_available


class LLMClientTests(unittest.TestCase):
    def _fake_response(self, content: str):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")
        return FakeResponse()

    def _capture_payload(self, **extra_env):
        captured = {}
        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return self._fake_response("ok")
        env = {"BRIEF_LLM_API_KEY": "sk-test", "BRIEF_LLM_MODEL": "test-model", **extra_env}
        with patch.dict(os.environ, env), patch("backend.llm.urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(chat_completion([{"role": "user", "content": "hi"}]), "ok")
        return captured["body"]

    def test_temperature_omitted_by_default(self):
        body = self._capture_payload()
        self.assertNotIn("temperature", body)
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["max_tokens"], 4096)

    def test_temperature_included_when_configured(self):
        body = self._capture_payload(BRIEF_LLM_TEMPERATURE="0.7")
        self.assertEqual(body["temperature"], 0.7)

    def test_invalid_temperature_is_ignored(self):
        body = self._capture_payload(BRIEF_LLM_TEMPERATURE="not-a-number")
        self.assertNotIn("temperature", body)

    def test_timeout_default_is_longer(self):
        with patch.dict(os.environ, {"BRIEF_LLM_API_KEY": "", "BRIEF_LLM_TIMEOUT": ""}, clear=True),              patch.object(Path, "read_text", return_value=""):
            self.assertEqual(_config()["timeout"], 30.0)

    def test_missing_key_raises(self):
        with patch.dict(os.environ, {"BRIEF_LLM_API_KEY": ""}):
            with self.assertRaises(RuntimeError):
                chat_completion([{"role": "user", "content": "hi"}])


if __name__ == "__main__":
    unittest.main()
