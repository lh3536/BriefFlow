"""RC2 provider truthfulness, live-data provenance and explainable calibration."""
from datetime import date
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from backend.llm import _config, chat_completion, llm_provider
from backend.input_agent.llm import validate_preference
from backend.input_agent.service import parse_user_request
from backend.router.service import run_brief_flow
from backend.ranking.service import rank_items

APP = str(Path(__file__).resolve().parents[1] / 'app.py')
QUERY = '我是金融专业大三学生，想找广州、深圳、香港、澳门适合本科生的金融、券商、投行和 FinTech 机会，优先实习和比赛，不要销售岗位。'
PREF = {'locations':['广州','深圳','香港','澳门'], 'categories':['实习','竞赛'],
        'keywords':['金融','券商','投行','FinTech'], 'exclude_keywords':['销售']}


def wording(messages, **kwargs):
    slots = json.loads(messages[-1]['content'])['approved_sentences']
    return json.dumps({'choices':[0] * len(slots)})


class RC2Tests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {'BRIEF_LLM_API_KEY':'', 'BRIEFFLOW_RETRIEVAL_MODE':'mock',
            'BRIEF_LLM_BASE_URL':'https://dashscope.aliyuncs.com/compatible-mode/v1', 'BRIEF_LLM_MODEL':'qwen-plus'}))

    def test_qwen_defaults_and_example_have_no_key(self):
        with patch.dict(os.environ, {}, clear=True), patch('backend.llm._load_dotenv'):
            config = _config()
        self.assertEqual(config['base_url'], 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.assertEqual(config['model'], 'qwen-plus')
        self.assertEqual(config['api_key'], '')
        example = Path(APP).with_name('.env.example').read_text(encoding='utf-8')
        self.assertIn('BRIEF_LLM_API_KEY=\n', example)

    def test_compatible_endpoint_can_still_be_overridden(self):
        with patch.dict(os.environ, {'BRIEF_LLM_BASE_URL':'https://example.com/v1','BRIEF_LLM_MODEL':'other-model'}):
            self.assertEqual(llm_provider(), 'openai-compatible')
            self.assertEqual(_config()['model'], 'other-model')

    def test_qwen_payload_uses_correct_endpoint_and_authorization(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"choices":[{"message":{"content":"ok"}}]}'
        def transport(request, **kwargs):
            self.assertEqual(request.full_url, 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions')
            self.assertEqual(json.loads(request.data)['model'], 'qwen-plus')
            self.assertEqual(request.get_header('Authorization'), 'Bearer test-placeholder')
            return Response()
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY':'test-placeholder'}), patch('urllib.request.urlopen',side_effect=transport):
            self.assertEqual(chat_completion([{'role':'user','content':'test'}]), 'ok')

    def test_input_synonyms_and_complete_explicit_preferences(self):
        raw = {**PREF, 'keywords':['金融','证券公司','投资银行','金融科技','fintech']}
        self.assertEqual(validate_preference(raw), PREF)
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY':'test-placeholder'}), patch(
                'backend.input_agent.llm.chat_completion',return_value=json.dumps(raw)):
            trace = {}
            pref = parse_user_request(QUERY, trace=trace)
        for field in PREF:
            self.assertEqual(set(pref[field]), set(PREF[field]))
        self.assertEqual(trace, {'input_mode':'llm','input_provider':'qwen'})

    def test_empty_llm_parse_does_not_claim_qwen_input_success(self):
        with patch('backend.input_agent.service.parse_with_llm',return_value={'keywords':[]}):
            trace = {}
            parse_user_request(QUERY,trace=trace)
        self.assertEqual(trace['input_mode'],'rule')

    def app(self):
        app = AppTest.from_file(APP).run()
        app.text_input[0].set_value(QUERY)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        return app

    def test_both_success_shows_qwen_enhanced_offline_transport(self):
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY':'test-placeholder'}), patch(
                'backend.input_agent.llm.chat_completion',return_value=json.dumps(PREF)), patch(
                'backend.output_agent.llm.chat_completion',side_effect=wording):
            app = self.app()
        result = app.session_state['search_result']
        self.assertEqual(result['input_provider'],'qwen')
        self.assertEqual(result['summary_provider'],'qwen')
        self.assertEqual(result['summary_mode'],'llm')
        self.assertTrue(any('Qwen Enhanced' in x.value for x in app.markdown))
        self.assertTrue(any('AI-generated Brief' in x.value for x in app.caption))
        self.assertTrue(2 <= result['summary'].count('。') <= 4)

    def test_key_without_success_never_shows_enhanced(self):
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY':'test-placeholder'}), patch(
                'backend.input_agent.llm.chat_completion',side_effect=TimeoutError), patch(
                'backend.output_agent.llm.chat_completion',side_effect=TimeoutError):
            app = self.app()
        self.assertFalse(any('Qwen Enhanced' in x.value for x in app.markdown))
        self.assertTrue(any('Rule-based Fallback' in x.value for x in app.markdown))

    def test_partial_input_failure_is_not_full_qwen_enhancement(self):
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY':'test-placeholder'}), patch(
                'backend.input_agent.llm.chat_completion',side_effect=TimeoutError), patch(
                'backend.output_agent.llm.chat_completion',side_effect=wording):
            app = self.app()
        self.assertFalse(any('Qwen Enhanced' in x.value for x in app.markdown))
        self.assertTrue(any('Rule-based Fallback' in x.value for x in app.markdown))
        self.assertEqual(app.session_state['search_result']['summary_mode'],'llm')

    def test_no_key_uses_no_network(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network')):
            app = self.app()
        self.assertEqual(app.session_state['search_result']['input_mode'],'rule')

    def test_live_records_filtered_to_zero_keep_web_provenance(self):
        record = {'title':'官方科研记录','location':'未注明','category':'科研','source':'UKRI'}
        with patch.dict(os.environ, {'BRIEFFLOW_RETRIEVAL_MODE':'web'}), patch(
                'backend.router.service.get_items',return_value=[record]):
            app = self.app()
        result = app.session_state['search_result']
        self.assertEqual(result['total_items'],0)
        self.assertEqual(result['retrieval']['retrieved_count'],1)
        self.assertEqual(result['retrieval']['data_source_mode'],'Web Data')
        self.assertEqual(app.metric[3].value,'Web Data')
        self.assertFalse(app.warning)

    def test_all_web_failures_use_explicit_mock_fallback(self):
        with patch.dict(os.environ, {'BRIEFFLOW_RETRIEVAL_MODE':'web'}), patch(
                'backend.retrieval.sources.urlopen',side_effect=OSError('offline')):
            app = self.app()
        self.assertEqual(app.metric[3].value,'Mock Data')
        self.assertTrue(app.session_state['search_result']['retrieval']['fallback'])
        self.assertTrue(any('本次使用 Demo Mock Data' in x.value for x in app.warning))

    def test_optional_rc2_metadata_missing(self):
        with patch('backend.router.service.run_brief_flow',return_value={
                'recommended_items':[{'title':'Only title'}], 'preference':{}, 'summary':'规则摘要。'}):
            app = self.app()
        self.assertFalse(any('Qwen Enhanced' in x.value for x in app.markdown))

    def test_complete_partial_and_unmatched_keywords_have_distinct_scores(self):
        pref = {'locations':['深圳'],'categories':['实习'],'keywords':['量化','投行']}
        rows = [{'job_id':str(i),'title':title,'location':'深圳','category':'实习'}
                for i,title in enumerate(['量化投行实习','量化实习','运营实习'])]
        ranked = rank_items(pref,rows,as_of=date(2026,10,13))
        self.assertEqual([x['match_score'] for x in ranked],[65,65,55])
        for row in ranked:
            self.assertEqual(sum(row['score_breakdown']['match'].values()),row['match_score'])
            self.assertEqual(sum(float(re.search(r'([+-]\d+(?:\.\d+)?)$',reason)[1])
                                 for reason in row['why_recommended']),row['match_score'])

    def test_generic_keyword_does_not_award_all_specialist_points(self):
        pref = {**PREF, 'locations':['深圳'],'categories':['实习']}
        row = {'title':'实习','location':'深圳','category':'实习'}
        result = rank_items(pref,[row],as_of=date(2026,10,13))[0]
        self.assertEqual(result['match_score'],55.0)


if __name__ == '__main__':
    unittest.main()
