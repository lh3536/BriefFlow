"""Optional LLM enhancement tests for the input/output agents.

All tests mock the LLM client: no network, no API key, deterministic.
The rule-based baseline must be identical whether the LLM is disabled,
broken or returns garbage.
"""
import json
import unittest
from unittest.mock import patch

from backend.input_agent.llm import merge_preferences, validate_preference
from backend.input_agent.service import parse_user_request
from backend.output_agent.service import build_brief
from backend.router.service import run_brief_flow

RULE_RESULT = {
    "categories": ["金融实习"],
    "locations": ["广州"],
    "keywords": ["金融"],
    "exclude_keywords": ["销售"],
}
DEMO_TEXT = "广州金融实习，不要销售岗"


def empty_preference():
    return {"categories": [], "locations": [], "keywords": [], "exclude_keywords": []}


class InputAgentLLMTests(unittest.TestCase):
    def test_llm_disabled_uses_rules(self):
        with patch("backend.input_agent.llm.llm_available", return_value=False):
            self.assertEqual(parse_user_request(DEMO_TEXT), RULE_RESULT)

    def test_llm_merges_with_rules(self):
        llm_json = json.dumps({
            "categories": ["金融实习"], "locations": ["广州"],
            "keywords": ["行研"], "exclude_keywords": [],
        }, ensure_ascii=False)
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion", return_value=llm_json) as chat:
            result = parse_user_request(DEMO_TEXT)
        self.assertEqual(result["categories"], ["金融实习"])
        self.assertEqual(result["locations"], ["广州"])
        self.assertEqual(result["keywords"], ["金融", "行研"])  # 规则在前，LLM 补充
        self.assertEqual(result["exclude_keywords"], ["销售"])  # 规则识别不被 LLM 弄丢
        self.assertEqual(chat.call_count, 1)

    def test_llm_invalid_json_retries_then_falls_back(self):
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion", return_value="这不是JSON") as chat:
            self.assertEqual(parse_user_request(DEMO_TEXT), RULE_RESULT)
        self.assertEqual(chat.call_count, 2)  # 重试 1 次后放弃

    def test_llm_network_error_falls_back(self):
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion", side_effect=OSError("boom")) as chat:
            self.assertEqual(parse_user_request(DEMO_TEXT), RULE_RESULT)
        self.assertEqual(chat.call_count, 2)

    def test_llm_unknown_values_filtered(self):
        llm_json = json.dumps({
            "categories": ["游戏公司", "金融实习"],
            "locations": ["北京", "深圳"],
            "keywords": ["金融", 123, None, "超长的关键词" * 10],
            "exclude_keywords": ["销售"],
            "hallucinated_field": ["应被忽略"],
        }, ensure_ascii=False)
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion", return_value=llm_json):
            result = parse_user_request("深圳有什么机会")
        self.assertEqual(result["categories"], ["金融实习"])  # 游戏公司被过滤
        self.assertEqual(result["locations"], ["深圳"])        # 北京被过滤
        self.assertEqual(result["keywords"], ["金融"])         # 非字符串/超长被过滤
        self.assertEqual(set(result), {"categories", "locations", "keywords", "exclude_keywords"})

    def test_llm_extracts_json_from_noisy_response(self):
        noisy = "好的，解析结果如下：\n```json\n{\"locations\": [\"香港\"]}\n```"
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion", return_value=noisy):
            result = parse_user_request("随便看看")
        self.assertEqual(result["locations"], ["香港"])

    def test_llm_not_called_for_blank_input(self):
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion") as chat:
            for text in ("", "  ", "　"):
                self.assertEqual(parse_user_request(text), empty_preference())
        chat.assert_not_called()

    def test_llm_enabled_non_string_still_raises(self):
        with patch("backend.input_agent.llm.llm_available", return_value=True):
            for value in (None, 123, [], {}):
                with self.assertRaises(ValueError):
                    parse_user_request(value)

    def test_contract_shape_with_llm(self):
        llm_json = '{"keywords": ["量化"], "locations": ["澳门"]}'
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion", return_value=llm_json):
            result = parse_user_request("澳门量化实习")
        self.assertEqual(set(result), {"categories", "locations", "keywords", "exclude_keywords"})
        for value in result.values():
            self.assertIsInstance(value, list)
            for item in value:
                self.assertIsInstance(item, str)
        self.assertEqual(json.loads(json.dumps(result, ensure_ascii=False)), result)


class InputAgentLLMHelperTests(unittest.TestCase):
    def test_validate_preference_drops_unknown_and_coerces(self):
        data = {"categories": ["金融实习", "未知类别"], "locations": "广州",
                "keywords": ["量化"], "exclude_keywords": []}
        result = validate_preference(data)
        self.assertEqual(result["categories"], ["金融实习"])
        self.assertEqual(result["locations"], [])  # 非列表字段按空处理
        self.assertEqual(result["keywords"], ["量化"])

    def test_merge_preferences_union_and_dedupe(self):
        rule = {**empty_preference(), "keywords": ["金融"]}
        llm = {**empty_preference(), "keywords": ["金融", "行研"]}
        self.assertEqual(merge_preferences(rule, llm)["keywords"], ["金融", "行研"])
        self.assertEqual(merge_preferences(rule, None), rule)


class OutputAgentLLMTests(unittest.TestCase):
    ITEMS = [
        {"job_id": "a", "title": "【模拟】投行分析实习", "location": "广州", "match_score": 100},
        {"job_id": "b", "title": "【模拟】行业研究实习", "location": "深圳", "match_score": 60},
    ]

    def test_llm_disabled_uses_deterministic_summary(self):
        with patch("backend.output_agent.llm.llm_available", return_value=False):
            result = build_brief(empty_preference(), self.ITEMS)
        self.assertEqual(result["summary"], "根据你的需求，本次找到 2 条匹配信息，其中 1 条高度匹配。")

    def test_llm_summary_used_when_valid(self):
        with patch("backend.output_agent.llm.llm_available", return_value=True), \
             patch("backend.output_agent.llm.chat_completion",
                   return_value="本次为你找到 2 条匹配，其中投行分析实习高度匹配，建议优先查看。"):
            result = build_brief(empty_preference(), self.ITEMS)
        self.assertEqual(result["summary"], "本次为你找到 2 条匹配，其中投行分析实习高度匹配，建议优先查看。")
        self.assertEqual(result["total_items"], 2)  # 其余契约字段不受影响
        self.assertEqual([i["job_id"] for i in result["recommended_items"]], ["a", "b"])

    def test_llm_summary_invalid_falls_back(self):
        for bad in ("", "  ", '{"summary": "JSON不行"}', "**加粗**不行", "长" * 200):
            with self.subTest(bad=bad), \
                 patch("backend.output_agent.llm.llm_available", return_value=True), \
                 patch("backend.output_agent.llm.chat_completion", return_value=bad):
                result = build_brief(empty_preference(), self.ITEMS)
            self.assertEqual(result["summary"], "根据你的需求，本次找到 2 条匹配信息，其中 1 条高度匹配。")

    def test_llm_summary_error_retries_then_falls_back(self):
        with patch("backend.output_agent.llm.llm_available", return_value=True), \
             patch("backend.output_agent.llm.chat_completion", side_effect=OSError("boom")) as chat:
            result = build_brief(empty_preference(), self.ITEMS)
        self.assertEqual(result["summary"], "根据你的需求，本次找到 2 条匹配信息，其中 1 条高度匹配。")
        self.assertEqual(chat.call_count, 2)

    def test_llm_summary_does_not_mutate_items(self):
        before = json.loads(json.dumps(self.ITEMS, ensure_ascii=False))
        with patch("backend.output_agent.llm.llm_available", return_value=True), \
             patch("backend.output_agent.llm.chat_completion", return_value="有效摘要。"):
            result = build_brief(empty_preference(), self.ITEMS)
        self.assertEqual(self.ITEMS, before)
        self.assertEqual(json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False))["recommended_items"], before)


class PipelineWithLLMTests(unittest.TestCase):
    def test_pipeline_survives_llm_failure(self):
        with patch("backend.input_agent.llm.llm_available", return_value=True), \
             patch("backend.output_agent.llm.llm_available", return_value=True), \
             patch("backend.input_agent.llm.chat_completion", side_effect=OSError("down")), \
             patch("backend.output_agent.llm.chat_completion", side_effect=OSError("down")):
            result = run_brief_flow(DEMO_TEXT)
        self.assertEqual(result["preference"], RULE_RESULT)
        self.assertGreater(result["total_items"], 0)
        self.assertTrue(result["summary"])


if __name__ == "__main__":
    unittest.main()
