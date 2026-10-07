"""Input / Output Agent contracts, edge cases and data-preservation checks."""
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch

from backend.input_agent.service import parse_user_request
from backend.output_agent.service import build_brief
from backend.router.service import run_brief_flow


def empty_preference():
    return {"categories": [], "locations": [], "keywords": [], "exclude_keywords": []}


class InputAgentTests(unittest.TestCase):
    def test_finance_request(self):
        result = parse_user_request("我是金融专业大三学生，想找广州深圳香港澳门的金融实习，不要销售岗。")
        self.assertEqual(result, {
            "categories": ["金融实习"],
            "locations": ["广州", "深圳", "香港", "澳门"],
            "keywords": ["金融"], "exclude_keywords": ["销售"],
        })
        self.assertEqual(json.loads(json.dumps(result, ensure_ascii=False)), result)

    def test_each_city(self):
        for city in ("广州", "深圳", "香港", "澳门"):
            with self.subTest(city=city):
                self.assertEqual(parse_user_request(f"想找{city}金融实习")["locations"], [city])

    def test_location_aliases_and_duplicates(self):
        for text, expected in (
            ("广深实习", ["广州", "深圳"]),
            ("港澳实习", ["香港", "澳门"]),
            ("粤港澳广州深圳广州实习", ["广州", "深圳", "香港", "澳门"]),
        ):
            with self.subTest(text=text):
                self.assertEqual(parse_user_request(text)["locations"], expected)

    def test_exclusion_expressions(self):
        for marker in ("不要", "排除", "不考虑", "不想要", "不想做", "不想找", "不接受", "避免"):
            with self.subTest(marker=marker):
                self.assertEqual(parse_user_request(f"金融实习，{marker}销售岗")["exclude_keywords"], ["销售"])

    def test_exclusion_stops_at_chinese_and_ascii_punctuation(self):
        for separator in (",", ";", ".", "!", "?", "，", "；", "。", "！", "？", "\n", "\r\n", "．"):
            with self.subTest(separator=separator):
                result = parse_user_request(f"不要销售岗{separator}广州金融实习")
                self.assertEqual(result["categories"], ["金融实习"])
                self.assertEqual(result["locations"], ["广州"])
                self.assertEqual(result["exclude_keywords"], ["销售"])

    def test_positive_request_after_exclusion(self):
        for resume in ("但想找", "不过想找", "想找", "希望", "只要", "要找", "需要"):
            with self.subTest(resume=resume):
                result = parse_user_request(f"不要销售岗{resume}深圳金融实习")
                self.assertEqual(result["locations"], ["深圳"])
                self.assertEqual(result["categories"], ["金融实习"])
                self.assertEqual(result["exclude_keywords"], ["销售"])

    def test_multiple_exclusions_without_false_positive_preference(self):
        result = parse_user_request("不要金融销售，也不考虑客服和保险，想找科研机会")
        self.assertEqual(result["categories"], ["科研机会"])
        self.assertEqual(result["keywords"], [])
        self.assertEqual(result["exclude_keywords"], ["销售", "客服", "保险"])
        self.assertEqual(parse_user_request("销售实习")["exclude_keywords"], [])

    def test_empty_input_and_pipeline(self):
        for text in ("", " \t\n", "　"):
            with self.subTest(text=text):
                self.assertEqual(parse_user_request(text), empty_preference())
                result = run_brief_flow(text)
                self.assertEqual(result["total_items"], 0)
                self.assertEqual(result["recommended_items"], [])
                self.assertTrue(result["summary"])

    def test_vague_request_keeps_only_recognized_preferences(self):
        self.assertEqual(parse_user_request("帮我看看有什么适合我的机会"), empty_preference())
        result = parse_user_request("想看看深圳有什么适合我的")
        self.assertEqual(result, {**empty_preference(), "locations": ["深圳"]})
        self.assertEqual(parse_user_request("不要销售岗"), {**empty_preference(), "exclude_keywords": ["销售"]})

    def test_non_string_input_reports_caller_error(self):
        for value in (None, 123, [], {}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_user_request(value)

    def test_runs_without_api_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            result = run_brief_flow("广州金融实习，不要销售岗")
        self.assertGreater(result["total_items"], 0)
        self.assertEqual(result["preference"]["exclude_keywords"], ["销售"])


class OutputAgentTests(unittest.TestCase):
    def test_json_contract(self):
        result = build_brief(empty_preference(), [{"job_id": "a", "match_score": 90}])
        self.assertEqual(set(result), {"preference", "total_items", "recommended_items", "summary", "summary_mode"})
        self.assertEqual(json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False)), result)
        self.assertEqual(result["total_items"], 1)
        self.assertIsInstance(result["summary"], str)

    def test_high_match_count_and_threshold(self):
        items = [{"match_score": score} for score in (0, 79, 79.9, 80, 90, 100)]
        result = build_brief(empty_preference(), items)
        self.assertEqual(result["summary"], "根据你的需求，本次找到 6 条匹配信息，其中 3 条高度匹配。")
        self.assertEqual(result["recommended_items"], items)

    def test_empty_recommendations(self):
        result = build_brief(empty_preference(), [])
        self.assertEqual(result["total_items"], 0)
        self.assertEqual(result["recommended_items"], [])
        self.assertIn("未找到匹配信息", result["summary"])
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)

    def test_preserves_all_item_data_and_order(self):
        items = [
            {"job_id": "b", "match_score": 81, "deadline": "2026-11-01", "source": {"name": "mock"}, "why_recommended": ["original"], "extra": [1, 2]},
            {"job_id": "a", "match_score": 100, "deadline": "2026-12-31", "source": "fixture"},
        ]
        before = deepcopy(items)
        result = build_brief(empty_preference(), items)
        self.assertEqual(items, before)
        self.assertEqual(result["recommended_items"], before)
        self.assertEqual([item["job_id"] for item in result["recommended_items"]], ["b", "a"])

    def test_returned_data_is_independent(self):
        preference = parse_user_request("广州金融实习")
        items = [{"match_score": 90, "source": {"name": "mock"}, "why_recommended": ["original"]}]
        result = build_brief(preference, items)
        result["preference"]["locations"].append("深圳")
        result["recommended_items"][0]["source"]["name"] = "changed"
        result["recommended_items"][0]["why_recommended"].append("changed")
        self.assertEqual(preference["locations"], ["广州"])
        self.assertEqual(items[0]["source"], {"name": "mock"})
        self.assertEqual(items[0]["why_recommended"], ["original"])

    def test_invalid_scores_not_counted_or_rewritten(self):
        items = [{}, *[{"match_score": score} for score in (None, True, "90", -1, 101)]]
        result = build_brief(empty_preference(), items)
        self.assertIn("其中 0 条高度匹配", result["summary"])
        self.assertEqual(result["recommended_items"], items)

    def test_nonfinite_scores_not_counted(self):
        # Such inputs violate the JSON contract, but must not inflate summary counts.
        result = build_brief(empty_preference(), [{"match_score": value} for value in (float("nan"), float("inf"), -float("inf"))])
        self.assertIn("其中 0 条高度匹配", result["summary"])


if __name__ == "__main__":
    unittest.main()
