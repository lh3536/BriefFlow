"""Router + real Streamlit script integration; LLM transport is mocked."""
from copy import deepcopy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from streamlit.testing.v1 import AppTest
from backend.router.service import run_brief_flow
from backend.retrieval.service import get_items
from backend.input_agent.service import parse_user_request

APP = str(Path(__file__).resolve().parents[1] / 'app.py')
QUERY = '我是金融专业大三学生，想找广州深圳香港澳门的金融实习，优先投行、券商和 FinTech，不要销售岗。'
SUMMARY = '本次为你找到金融实习机会，建议关注广州和深圳的岗位。'

class StreamlitIntegrationTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'BRIEF_LLM_API_KEY': '', 'BRIEFFLOW_RETRIEVAL_MODE': 'mock'})
        env.start()
        self.addCleanup(env.stop)

    def search(self):
        app = AppTest.from_file(APP).run()
        app.text_input[0].set_value(QUERY)
        return app.button[0].click().run()

    def test_no_key_full_pipeline_ui_and_rerun(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('No HTTP needed')):
            app = self.search()
            self.assertFalse(app.exception)
            result = app.session_state['search_result']
            self.assertTrue({'preference', 'summary', 'total_items', 'recommended_items'} <= result.keys())
            self.assertGreater(result['total_items'], 0)
            self.assertEqual(result['summary_mode'], 'deterministic')
            self.assertIn(result['summary'], [x.value for x in app.info])
            self.assertIn('🤖 AI Brief', [x.value for x in app.subheader])
            self.assertIn('🧠 Understood Preference', [x.value for x in app.subheader])
            self.assertTrue(any('Rule Fallback' in x.value for x in app.markdown))
            self.assertTrue(any('Demo / Mock Data' in x.value for x in app.warning))
            app.selectbox[0].select(10).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['search_result'], result)
            self.assertEqual(len(app.metric), 2 * min(10, result['total_items']))

    def test_valid_llm_enhances_preference_and_summary_in_ui(self):
        response = json.dumps({'keywords': ['FinTech', '券商']})
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY': 'test-placeholder'}), \
             patch('backend.input_agent.llm.chat_completion', return_value=response), \
             patch('backend.output_agent.llm.chat_completion', return_value=SUMMARY):
            app = self.search()
        self.assertFalse(app.exception)
        result = app.session_state['search_result']
        self.assertIn('FinTech', result['preference']['keywords'])
        self.assertIn('销售', result['preference']['exclude_keywords'])
        self.assertEqual(result['summary'], SUMMARY)
        self.assertEqual(result['summary_mode'], 'llm')
        self.assertIn(SUMMARY, [x.value for x in app.info])
        self.assertIn('LLM Summary', [x.value for x in app.caption])
        self.assertTrue(any('LLM Enhanced' in x.value for x in app.markdown))

    def test_llm_failures_preserve_deterministic_pipeline(self):
        # Reuse one retrieval snapshot: fetched_at legitimately changes per fetch.
        snapshot = get_items(parse_user_request(QUERY))
        self.enterContext(patch("backend.router.service.get_items", return_value=snapshot))
        baseline = run_brief_flow(QUERY)
        failures = [TimeoutError(), URLError('unavailable'), HTTPError('https://example.com', 500, 'error', {}, None)]
        for failure in failures:
            with self.subTest(kind=type(failure).__name__), \
                 patch.dict(os.environ, {'BRIEF_LLM_API_KEY': 'test-placeholder'}), \
                 patch('backend.input_agent.llm.chat_completion', side_effect=failure), \
                 patch('backend.output_agent.llm.chat_completion', side_effect=failure):
                self.assertEqual(run_brief_flow(QUERY), baseline)
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY': 'test-placeholder'}), \
             patch('backend.input_agent.llm.chat_completion', return_value='invalid JSON'), \
             patch('backend.output_agent.llm.chat_completion', return_value='{}'):
            app = self.search()
            self.assertEqual(app.session_state['search_result'], baseline)
            self.assertIn('Deterministic Fallback Summary', [x.value for x in app.caption])

    def test_summary_cannot_change_ranking_data(self):
        # Reuse one retrieval snapshot: fetched_at legitimately changes per fetch.
        snapshot = get_items(parse_user_request(QUERY))
        self.enterContext(patch("backend.router.service.get_items", return_value=snapshot))
        baseline = run_brief_flow(QUERY)
        with patch('backend.output_agent.llm.llm_available', return_value=True), \
             patch('backend.output_agent.llm.chat_completion', return_value=SUMMARY):
            enhanced = run_brief_flow(QUERY)
        self.assertEqual(enhanced['recommended_items'], baseline['recommended_items'])

    def test_optional_fields_missing_for_each_source(self):
        for source in (None, 'BriefFlow Mock', 'SQLite', 'Web'):
            minimal = {'title': '金融实习', 'category': '金融实习', 'location': '广州'}
            if source:
                minimal['source'] = source
            before = deepcopy(minimal)
            with self.subTest(source=source), patch('backend.router.service.get_items', return_value=[minimal]):
                app = self.search()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['search_result']['total_items'], 1)
                self.assertEqual(minimal, before)

    def test_pipeline_error_clears_previous_result_without_leaking_details(self):
        app = self.search()
        with patch('backend.router.service.run_brief_flow', side_effect=RuntimeError('private-detail')):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 1)
        self.assertNotIn('private-detail', app.error[0].value)
        self.assertNotIn('search_result', app.session_state)
        self.assertFalse(app.success)

    def test_web_mock_fallback_is_visible(self):
        with patch.dict(os.environ, {'BRIEFFLOW_RETRIEVAL_MODE': 'web'}), \
             patch('backend.retrieval.service.fetch_ukri', side_effect=OSError('offline')):
            app = self.search()
        self.assertFalse(app.exception)
        self.assertTrue(any('回退到 Mock Data' in x.value for x in app.warning))

if __name__ == '__main__':
    unittest.main()
