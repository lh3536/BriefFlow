"""HTTP integration tests; application logic stays in the existing Router."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.api import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        environment = patch.dict(os.environ, {'BRIEFFLOW_RETRIEVAL_MODE': 'mock'})
        environment.start()
        self.addCleanup(environment.stop)

    def test_brief_runs_existing_pipeline(self):
        response = self.client.post('/api/brief', json={'user_text': '粤港澳金融实习，不要销售岗'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['total_items'], 9)
        self.assertEqual(body['preference']['exclude_keywords'], ['销售'])
        self.assertTrue(all(item['source'] == 'BriefFlow Mock' for item in body['recommended_items']))
        self.assertIn('priority_score', body['recommended_items'][0])

    def test_empty_and_blank_requests_rejected(self):
        for value in ('', '  ', '\n\t'):
            with self.subTest(value=value):
                self.assertEqual(self.client.post('/api/brief', json={'user_text': value}).status_code, 422)

    def test_missing_and_wrong_types_rejected(self):
        for payload in ({}, {'user_text': None}, {'user_text': 123}, {'user_text': []}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/brief', json=payload).status_code, 422)

    def test_long_input_rejected(self):
        self.assertEqual(self.client.post('/api/brief', json={'user_text': 'x' * 2001}).status_code, 422)

    def test_pipeline_error_is_safe_and_server_recovers(self):
        with patch('backend.api.run_brief_flow', side_effect=RuntimeError('private internal error')), self.assertLogs('backend.api', level='ERROR'):
            response = self.client.post('/api/brief', json={'user_text': '金融实习'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {'detail': 'Unable to generate brief. Please try again.'})
        self.assertNotIn('private internal error', response.text)
        self.assertEqual(self.client.get('/api/health').status_code, 200)
        self.assertEqual(self.client.post('/api/brief', json={'user_text': '金融实习'}).status_code, 200)

    def test_returns_router_response_without_rewriting(self):
        result = {'preference': {}, 'total_items': 0, 'recommended_items': [], 'summary': 'unchanged'}
        with patch('backend.api.run_brief_flow', return_value=result) as router:
            response = self.client.post('/api/brief', json={'user_text': '  我的需求  '})
        router.assert_called_once_with('我的需求')
        self.assertEqual(response.json(), result)

    def test_no_matches_is_success(self):
        body = self.client.post('/api/brief', json={'user_text': '未知的需求'}).json()
        self.assertEqual(body['total_items'], 0)
        self.assertEqual(body['recommended_items'], [])

    def test_invalid_json_does_not_crash(self):
        response = self.client.post('/api/brief', content='{broken', headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 422)

    def test_get_cannot_trigger_pipeline(self):
        self.assertEqual(self.client.get('/api/brief').status_code, 405)


if __name__ == '__main__':
    unittest.main()
