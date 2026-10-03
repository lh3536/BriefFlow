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
    "categories": ["金融实习"],
    "locations": ["广州", "深圳", "香港", "澳门"],
    "keywords": ["金融"],
    "exclude_keywords": ["销售"],
}


class PipelineTests(unittest.TestCase):
    def test_parse_user_request(self):
        self.assertEqual(parse_user_request(REQUEST), PREFERENCE)

    def test_regional_alias(self):
        self.assertEqual(parse_user_request("我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。"), PREFERENCE)

    def test_blank_input(self):
        with self.assertRaises(ValueError):
            parse_user_request("   ")

    def test_mock_data_read(self):
        items = get_items(PREFERENCE)
        self.assertEqual(len(items), 15)
        self.assertEqual(items[0]["job_id"], "job_001")
        self.assertEqual(set(items[0]), {
            "job_id", "title", "company", "location", "category", "deadline",
            "link", "match_score", "why_recommended",
        })

    def test_exclusions_filter_actual_sales_content(self):
        # Existing mock data contains no sales roles: inject candidates to test exclusion.
        safe = get_items(PREFERENCE)[0]
        candidates = [safe] + [
            {**safe, "job_id": f"sales_{field}", field: "金融销售"}
            for field in ("title", "company", "category")
        ]
        preference = {**PREFERENCE, "categories": []}
        self.assertEqual(len(rank_items({**preference, "exclude_keywords": []}, candidates)), 4)
        self.assertEqual([item["job_id"] for item in rank_items(preference, candidates)], ["job_001"])

    def test_ranking_results_and_input_unchanged(self):
        items = get_items(PREFERENCE)
        before = deepcopy(items)
        result = rank_items(PREFERENCE, items)
        self.assertEqual(len(result), 9)
        self.assertEqual(items, before)
        self.assertTrue(all(item["match_score"] == 100 for item in result))
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
        self.assertEqual([item["match_score"] for item in result], [100, 80, 80])

    def test_location_and_category_filter(self):
        result = run_brief_flow("想找深圳金融实习，不要销售岗。")
        self.assertEqual([item["job_id"] for item in result["recommended_items"]], ["job_002", "job_005", "job_009"])

    def test_full_pipeline(self):
        result = run_brief_flow(REQUEST)
        self.assertEqual(result["preference"], PREFERENCE)
        self.assertEqual(result["total_items"], 9)
        self.assertEqual(result["recommended_items"][0]["job_id"], "job_001")

    def test_json_output_contract(self):
        result = run_brief_flow(REQUEST)
        self.assertEqual(set(result), {"preference", "total_items", "recommended_items"})
        self.assertEqual(result["total_items"], len(result["recommended_items"]))
        self.assertEqual(json.loads(json.dumps(result, ensure_ascii=False)), result)
        self.assertTrue(all(isinstance(values, list) for values in result["preference"].values()))

    def test_empty_output(self):
        self.assertEqual(build_brief(PREFERENCE, []), {
            "preference": PREFERENCE, "total_items": 0, "recommended_items": [],
        })
        self.assertEqual(run_brief_flow("未识别的需求")["recommended_items"], [])


if __name__ == "__main__":
    unittest.main()
