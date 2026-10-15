"""Behavior and integration checks for the V0.1 mock pipeline."""
from copy import deepcopy
import json
import unittest

from backend.input_agent.service import parse_user_request
from backend.output_agent.service import build_brief
from backend.ranking.service import rank_items
from backend.retrieval.service import get_items
from backend.router.service import run_brief_flow

REQUEST = "我是金融专业大三学生，想找广州深圳香港澳门的金融实习，不要销售岗。"
PREFERENCE = {
    "categories": ["实习"],
    "locations": ["广州", "深圳", "香港", "澳门"],
    "keywords": ["金融"],
    "exclude_keywords": ["销售"],
}


class PipelineTests(unittest.TestCase):
    def test_parse_user_request(self):
        # 依赖 A0 输出新 category，A0 未改前会挂
        self.assertEqual(parse_user_request(REQUEST), PREFERENCE)

    def test_regional_alias(self):
        # 同上
        self.assertEqual(parse_user_request("我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。"), PREFERENCE)

    def test_blank_input(self):
        self.assertEqual(parse_user_request("   "), {
            "categories": [], "locations": [], "keywords": [], "exclude_keywords": [],
        })

    def test_mock_data_read(self):
        items = get_items(PREFERENCE)
        self.assertEqual(len(items), 60)
        self.assertEqual(items[0]["job_id"], "job_101")
        self.assertTrue({
            "job_id", "title", "company", "location", "category", "deadline",
            "link", "match_score", "why_recommended",
        }.issubset(items[0]))
        self.assertEqual(items[0]["source"], "BriefFlow Mock")
        self.assertEqual(items[0]["source_url"], items[0]["link"])
        self.assertEqual(items[0]["organization"], items[0]["company"])

    def test_exclusions_filter_actual_sales_content(self):
        safe = get_items(PREFERENCE)[0]
        candidates = [safe] + [
            {**safe, "job_id": f"sales_{field}", field: "金融销售"}
            for field in ("title", "company", "category")
        ]
        preference = {**PREFERENCE, "categories": []}
        self.assertEqual(len(rank_items({**preference, "exclude_keywords": []}, candidates)), 4)
        self.assertEqual([item["job_id"] for item in rank_items(preference, candidates)], ["job_101"])

    def test_ranking_results_and_input_unchanged(self):
        items = get_items(PREFERENCE)
        before = deepcopy(items)
        result = rank_items(PREFERENCE, items)
        # 新数据里 category="实习" + 大湾区 location 有 4 条
        self.assertEqual(len(result), 4)
        self.assertEqual(items, before)
        for item in result:
            self.assertEqual(sum(int(reason.rsplit("+", 1)[1]) for reason in item["why_recommended"]), item["match_score"])

    def test_ranking_order_and_tie_break(self):
        base = get_items(PREFERENCE)[0]
        items = [
            {**base, "job_id": "b", "title": "金融实习"},
            {**base, "job_id": "z", "title": "金融量化实习"},
            {**base, "job_id": "a", "title": "金融实习"},
        ]
        result = rank_items({**PREFERENCE, "keywords": ["量化"]}, items)
        self.assertEqual([item["job_id"] for item in result], ["z", "a", "b"])
        self.assertEqual([item["match_score"] for item in result], [65, 55, 55])

    def test_location_and_category_filter(self):
        # 依赖 A0 输出新 category，A0 未改前会挂
        result = run_brief_flow("想找深圳金融实习，不要销售岗。")
        self.assertEqual([item["job_id"] for item in result["recommended_items"]], ["job_102", "job_104"])

    def test_full_pipeline(self):
        # 依赖 A0 输出新 category，A0 未改前会挂
        result = run_brief_flow(REQUEST)
        self.assertEqual(result["preference"], PREFERENCE)
        self.assertEqual(result["total_items"], 4)
        self.assertEqual(result["recommended_items"][0]["job_id"], "job_103")

    def test_json_output_contract(self):
        result = run_brief_flow(REQUEST)
        self.assertEqual(set(result), {
            "preference", "total_items", "recommended_items", "summary",
            "summary_mode", "summary_provider", "highlights", "result_stats",
            "input_mode", "input_provider", "retrieval", "tier", "gated",
        })
        self.assertIsInstance(result["summary"], str)
        self.assertEqual(json.loads(json.dumps(result, ensure_ascii=False)), result)
        self.assertTrue(all(isinstance(values, list) for values in result["preference"].values()))

    def test_empty_output(self):
        empty = build_brief(PREFERENCE, [])
        self.assertEqual(empty["preference"], PREFERENCE)
        self.assertEqual(empty["total_items"], 0)
        self.assertEqual(empty["recommended_items"], [])
        self.assertIn("未找到匹配信息", empty["summary"])
        self.assertEqual(run_brief_flow("未识别的需求")["recommended_items"], [])


if __name__ == "__main__":
    unittest.main()