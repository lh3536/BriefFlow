"""RC output acceptance: grounding, source honesty and unchanged ranking."""
from copy import deepcopy
from datetime import date, datetime
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from backend.output_agent.service import build_brief
from backend.output_agent.presentation import describe_items, sentence_options
from backend.ranking.service import rank_items

APP = str(Path(__file__).resolve().parents[1] / 'app.py')
TODAY = date(2026, 10, 12)
PREF = {'locations': ['深圳'], 'categories': ['金融实习'], 'keywords': ['投行'], 'exclude_keywords': ['销售']}


def item(**changes):
    return {'job_id': 'a', 'title': '深圳投行实习', 'location': '深圳',
            'category': '金融实习', 'organization': '测试机构', 'source': 'BriefFlow Mock',
            'deadline': '2026-10-15', 'match_score': 90, 'priority_score': 85,
            'why_recommended': ['地点匹配（深圳）+40'], **changes}


class OutputRCTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {'BRIEF_LLM_API_KEY': '', 'BRIEFFLOW_RETRIEVAL_MODE': 'mock'}))
        clock = self.enterContext(patch('backend.output_agent.presentation.datetime'))
        clock.now.return_value = datetime(2026, 10, 12, 12)

    def test_old_fields_and_additive_metadata(self):
        result = build_brief(PREF, [item()])
        self.assertTrue({'preference', 'total_items', 'recommended_items', 'summary', 'summary_mode'} <= result.keys())
        self.assertIsInstance(result['highlights'], list)
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_zero_results(self):
        result = build_brief(PREF, [])
        self.assertEqual(result['total_items'], 0)
        self.assertEqual(result['result_stats']['urgent_deadline'], 0)
        self.assertIn('未找到', result['summary'])
        self.assertNotIn('《', result['summary'])

    def test_single_result_has_only_existing_title(self):
        result = build_brief(PREF, [item()])
        self.assertIn('1 条与你需求相关', result['summary'])
        self.assertEqual(result['summary'].count('《'), 1)
        self.assertIn('《深圳投行实习》', result['summary'])
        self.assertNotIn('香港', result['summary'])

    def test_high_match_invalid_and_boundary_scores(self):
        scores = [79.9, 80, 100, 101, True, '90', None, float('inf'), float('nan')]
        stats = describe_items([item(match_score=score) for score in scores], as_of=TODAY)
        self.assertEqual(stats['high_match'], 2)

    def test_deadline_boundaries_unknown_and_expired(self):
        dates = ['2026-10-11', '2026-10-12', '2026-10-19', '2026-10-20', '', '2026-02-30', None]
        result = build_brief(PREF, [item(deadline=value) for value in dates])
        self.assertEqual(result['result_stats']['urgent_deadline'], 2)
        self.assertEqual(result['result_stats']['expired'], 1)
        self.assertIn('2 条 7 天内截止', result['highlights'])
        self.assertIn('2 条机会将在 7 天内截止', result['summary'])

    def test_expired_only_does_not_urge_application(self):
        result = build_brief(PREF, [item(deadline='2026-10-01')])
        self.assertNotIn('建议先查看《', result['summary'])
        self.assertIn('1 条已过标注截止', result['summary'])

    def test_mock_and_live_modes(self):
        self.assertEqual(describe_items([item()], requested_mode='mock')['data_source_mode'], 'Mock Data')
        for mode, label in [('web', 'Web'), ('database', 'Database')]:
            with self.subTest(mode=mode):
                stats = describe_items([item(source='Official fixture')], requested_mode=mode)
                self.assertEqual(stats['data_source_mode'], label)
                self.assertFalse(stats['retrieval_fallback'])
                fallback = describe_items([item()], requested_mode=mode)
                self.assertEqual(fallback['data_source_mode'], 'Mock Data')
                self.assertTrue(fallback['retrieval_fallback'])

    def test_empty_live_result_does_not_claim_verified_source(self):
        stats = describe_items([], requested_mode='web')
        self.assertIn('来源未确认', stats['data_source_mode'])
        self.assertFalse(stats['retrieval_fallback'])

    def test_mixed_sources_label(self):
        stats = describe_items([item(), item(source='Official fixture')], requested_mode='web')
        self.assertEqual(stats['data_source_mode'], 'Mixed / 含 Mock Data')
        self.assertEqual(stats['mock_count'], 1)

    def test_llm_failure_keeps_deterministic_summary(self):
        baseline = build_brief(PREF, [item()])
        with patch('backend.output_agent.llm.llm_available', return_value=True), patch(
                'backend.output_agent.llm.chat_completion', side_effect=TimeoutError):
            self.assertEqual(build_brief(PREF, [item()]), baseline)

    def test_llm_cannot_invent_items_numbers_or_claims(self):
        baseline = build_brief(PREF, [item()])
        for response in ['香港新增 100 个高薪岗位。', '{"choices": [0,0,0,0], "extra": "保证录用"}',
                         '{"choices": [100,0,0,0]}', '{"choices": [true,0,0,0]}',
                         '{"choices": [-1,0,0,0]}', '{"choices": [0]}', '[]']:
            with self.subTest(response=response), patch('backend.output_agent.llm.llm_available', return_value=True), patch(
                    'backend.output_agent.llm.chat_completion', return_value=response):
                self.assertEqual(build_brief(PREF, [item()]), baseline)

    def test_valid_llm_choices_produce_only_grounded_facts(self):
        items = [item()]
        options = sentence_options(items, describe_items(items))
        choices = [len(slot) - 1 for slot in options]
        with patch('backend.output_agent.llm.llm_available', return_value=True), patch(
                'backend.output_agent.llm.chat_completion', return_value=json.dumps({'choices': choices})):
            result = build_brief(PREF, items)
        self.assertEqual(result['summary_mode'], 'llm')
        self.assertEqual(result['summary'], ''.join(slot[i] for slot, i in zip(options, choices)))
        self.assertEqual(result['recommended_items'], items)

    def test_output_never_changes_ranking_or_input(self):
        ranked = rank_items(PREF, [item(job_id='b', deadline='2026-12-01'), item()], as_of=TODAY)
        before = deepcopy(ranked)
        result = build_brief(PREF, ranked)
        self.assertEqual(result['recommended_items'], before)
        self.assertEqual(ranked, before)
        result['recommended_items'][0]['why_recommended'].append('changed')
        self.assertEqual(ranked, before)

    def run_ui(self, result):
        with patch('backend.router.service.run_brief_flow', return_value=result):
            app = AppTest.from_file(APP).run()
            app.button[0].click().run()
        self.assertFalse(app.exception)
        return app

    def test_legacy_optional_fields_missing_in_streamlit(self):
        app = self.run_ui({'preference': {}, 'total_items': 1,
                           'recommended_items': [{'title': '仅标题'}], 'summary': '测试摘要'})
        self.assertIn('Rule-based Brief', [entry.value for entry in app.caption])
        self.assertEqual(app.metric[0].value, '1')

    def test_zero_results_streamlit(self):
        app = self.run_ui(build_brief(PREF, []))
        self.assertFalse(app.selectbox)
        self.assertEqual(app.metric[0].value, '0')

    def test_ui_counts_actual_items_not_optional_numbers(self):
        result = build_brief(PREF, [item()])
        result['total_items'] = 999
        result['result_stats']['high_match'] = 999
        app = self.run_ui(result)
        self.assertEqual([entry.value for entry in app.metric[:3]], ['1', '1', '1'])
        self.assertTrue(any('地点匹配（深圳）' in entry.value and '+40' not in entry.value for entry in app.markdown))

    def test_configured_key_does_not_mislabel_rule_brief(self):
        result = build_brief(PREF, [item()])
        with patch.dict(os.environ, {'BRIEF_LLM_API_KEY': 'test-placeholder'}):
            app = self.run_ui(result)
        self.assertTrue(any('Rule-based Brief' in entry.value for entry in app.markdown))
        self.assertFalse(any('AI-generated Brief' in entry.value for entry in app.markdown))


if __name__ == '__main__':
    unittest.main()
