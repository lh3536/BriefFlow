"""Configuration is safe and bounded; never use real credentials in tests."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from backend.llm import _config, _load_dotenv, llm_available

class LLMConfigurationTests(unittest.TestCase):
    def test_dotenv_only_loads_supported_settings(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, 'read_text', return_value='BRIEF_LLM_MODEL=test-model\nUNRELATED_SETTING=ignored'):
            _load_dotenv()
            self.assertEqual(os.environ['BRIEF_LLM_MODEL'], 'test-model')
            self.assertNotIn('UNRELATED_SETTING', os.environ)

    def test_environment_overrides_dotenv_including_empty_key(self):
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY': ''}), patch.object(Path, 'read_text', return_value='BRIEF_LLM_API_KEY=test-placeholder'):
            self.assertFalse(llm_available())

    def test_invalid_timeouts_default(self):
        for timeout in ('0', '-1', 'nan', 'inf', 'invalid'):
            with self.subTest(timeout=timeout), patch.dict(os.environ, {'BRIEF_LLM_TIMEOUT': timeout}):
                self.assertEqual(_config()['timeout'], 8.0)

    def test_unreadable_dotenv_is_optional(self):
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY': ''}), patch.object(Path, 'read_text', side_effect=UnicodeError()):
            self.assertFalse(llm_available())
