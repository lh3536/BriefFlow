"""Deterministic scoring policy checks with a fixed business date."""
from copy import deepcopy
from datetime import date, timedelta
import json
import os
import re
import unittest
from unittest.mock import patch

from backend.ranking.service import rank_items

TODAY = date(2026, 10, 4)


def item(id="a", **changes):
    return {"job_id": id, "title": "量化实习", "company": "示范机构", "location": "深圳",
            "category": "金融实习", "deadline": "", "published_at": "", **changes}


def preference(**changes):
    return {"locations": ["深圳"], "categories": ["金融实习"],
            "keywords": ["量化"], "exclude_keywords": [], **changes}


def rank(pref, items, **kwargs):
    return rank_items(pref, items, as_of=TODAY, **kwargs)


class RankingTests(unittest.TestCase):
    def test_location_adds_match_points(self):
        self.assertEqual(rank(preference(), [item()])[0]["match_score"], 100)
        self.assertEqual(rank(preference(locations=[]), [item()])[0]["match_score"], 60)

    def test_category_adds_match_points(self):
        self.assertEqual(rank(preference(categories=[]), [item()])[0]["match_score"], 60)

    def test_keyword_adds_match_points(self):
        scores = rank(preference(), [item("yes"), item("no", title="运营实习")])
        self.assertEqual([row["match_score"] for row in scores], [100, 80])

    def test_location_and_category_remain_hard_filters(self):
        self.assertEqual(rank(preference(), [item(location="广州"), item(category="科研机会")]), [])

    def test_sales_exclusions_and_aliases_are_hard_filters(self):
        for term in ("销售", "保险代理", "电话营销", "地推", "客服销售"):
            for field in ("title", "summary", "company", "organization", "tags", "requirements"):
                with self.subTest(term=term, field=field):
                    value = [term] if field in ("tags", "requirements") else term
                    self.assertEqual(rank(preference(exclude_keywords=["销售"]), [item(**{field: value})]), [])

    def test_old_explanations_do_not_trigger_exclusion_or_keyword_match(self):
        row = item(title="实习", why_recommended=["量化销售 +100"])
        result = rank(preference(exclude_keywords=["销售"]), [row])
        self.assertEqual(result[0]["match_score"], 80)

    def test_deadline_increases_priority_even_at_full_match(self):
        result = rank(preference(), [item("later", deadline="2026-11-01"), item("soon", deadline="2026-10-06")])
        self.assertEqual([row["job_id"] for row in result], ["soon", "later"])
        self.assertEqual([row["priority_score"] for row in result], [90, 80])

    def test_freshness_increases_priority(self):
        result = rank(preference(), [item("old", published_at="2026-08-01"), item("new", published_at="2026-10-03")])
        self.assertEqual([row["job_id"] for row in result], ["new", "old"])
        self.assertEqual([row["priority_score"] for row in result], [90, 80])

    def test_deadline_band_boundaries(self):
        for days, bonus in ((0, 10), (3, 10), (4, 6), (7, 6), (8, 3), (14, 3), (15, 0)):
            with self.subTest(days=days):
                row = rank(preference(), [item(deadline=(TODAY + timedelta(days=days)).isoformat())])[0]
                self.assertEqual(row["score_breakdown"]["priority"]["deadline"], bonus)

    def test_freshness_boundaries_and_future_dates(self):
        for days, bonus in ((-1, 0), (0, 10), (7, 10), (8, 5), (30, 5), (31, 0)):
            with self.subTest(days=days):
                row = rank(preference(), [item(published_at=(TODAY - timedelta(days=days)).isoformat())])[0]
                self.assertEqual(row["score_breakdown"]["priority"]["freshness"], bonus)

    def test_expired_keeps_match_but_zeroes_delivery_priority(self):
        result = rank(preference(), [item("expired", deadline="2026-10-03", published_at="2026-10-02"), item("active")])
        self.assertEqual(result[-1]["job_id"], "expired")
        self.assertEqual(result[-1]["match_score"], 100)
        self.assertEqual(result[-1]["priority_score"], 0)
        self.assertTrue(result[-1]["deadline_expired"])

    def test_same_input_and_reversed_input_rank_identically(self):
        items = [item("c"), item("a"), item("b")]
        result = rank(preference(), items)
        self.assertEqual(result, rank(preference(), items))
        self.assertEqual(result, rank(preference(), list(reversed(items))))
        self.assertEqual([row["final_rank"] for row in result], [1, 2, 3])

    def test_tie_breaker_deadline_then_publication_then_id(self):
        rows = [item("z", deadline="2026-12-01"), item("b", deadline="2026-11-01", published_at="2026-08-01"),
                item("a", deadline="2026-11-01", published_at="2026-08-01"), item("newer", deadline="2026-11-01", published_at="2026-09-01")]
        self.assertEqual([row["job_id"] for row in rank(preference(), rows)], ["newer", "a", "b", "z"])

    def test_keyword_preference_reverses_ranking(self):
        rows = [item("quant", title="量化实习"), item("research", title="行研实习")]
        self.assertEqual(rank(preference(keywords=["量化"]), rows)[0]["job_id"], "quant")
        self.assertEqual(rank(preference(keywords=["行研"]), rows)[0]["job_id"], "research")

    def test_explicit_preference_priority_changes_order(self):
        rows = [item("keyword"), item("urgent", title="实习", deadline="2026-10-05", published_at="2026-10-04")]
        self.assertEqual(rank(preference(), rows)[0]["job_id"], "urgent")
        self.assertEqual(rank(preference(priority_weights={"keyword": 3}), rows)[0]["job_id"], "keyword")

    def test_explanations_and_breakdowns_reconcile(self):
        for overrides in ({}, {"priority_weights": {"keyword": 3}}, {"priority_weights": {"location": 0.3, "category": 0.7}}):
            for deadline in ("2026-10-05", "2026-10-01"):
                row = rank(preference(**overrides), [item(deadline=deadline, published_at="2026-10-03")])[0]
                for score, reasons, group in (("match_score", "why_recommended", "match"), ("priority_score", "priority_reasons", "priority")):
                    self.assertAlmostEqual(sum(row["score_breakdown"][group].values()), row[score])
                    self.assertAlmostEqual(sum(float(re.search(r"([+-]\d+(?:\.\d+)?)$", reason)[1]) for reason in row[reasons]), row[score])

    def test_empty_data_and_unrecognized_preferences(self):
        self.assertEqual(rank(preference(), []), [])
        self.assertEqual(rank({}, [item()]), [])

    def test_missing_invalid_dates_are_neutral(self):
        for value in (None, "", "bad", "2026-02-30", [], 123):
            with self.subTest(value=value):
                row = rank(preference(), [item(deadline=value, published_at=value)])[0]
                self.assertEqual(row["priority_score"], 80)
        row = item()
        del row["deadline"], row["published_at"]
        self.assertEqual(rank(preference(), [row])[0]["priority_score"], 80)

    def test_scores_bounded_with_custom_and_invalid_weights(self):
        for weights in ({"keyword": 3}, {"location": 0, "category": 0, "keyword": 0}, {"keyword": float("nan")}, {"location": -1}, {"category": True}, {"keyword": 10**1000}, "invalid"):
            with self.subTest(weights=str(weights)[:50]):
                row = rank(preference(priority_weights=weights), [item(deadline="2026-10-05", published_at="2026-10-04")])[0]
                self.assertTrue(0 <= row["match_score"] <= 100)
                self.assertTrue(0 <= row["priority_score"] <= 100)
                self.assertTrue(all(value >= 0 for value in row["score_breakdown"]["match"].values()))

    def test_feedback_hook_is_explicitly_noop(self):
        with self.assertLogs("backend.ranking.service", level="INFO"):
            actual = rank(preference(), [item()], user_feedback_weights={"销售": -100})
        self.assertEqual(actual, rank(preference(), [item()]))

    def test_inputs_and_source_metadata_preserved(self):
        pref = preference()
        rows = [item(source="fixture", source_url="https://example.com", requirements=["original"])]
        before = deepcopy((pref, rows))
        result = rank(pref, rows)
        self.assertEqual((pref, rows), before)
        self.assertEqual(result[0]["source"], "fixture")
        result[0]["requirements"].append("changed")
        self.assertEqual(rows[0]["requirements"], ["original"])

    def test_no_api_key_and_json_output(self):
        with patch.dict(os.environ, {}, clear=True):
            result = rank(preference(), [item()])
        self.assertEqual(json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False)), result)

    def test_canonical_item_id_supported(self):
        row = item(item_id="canonical")
        del row["job_id"]
        self.assertEqual(rank(preference(), [row])[0]["final_rank"], 1)

    def test_malformed_items_and_empty_terms_do_not_match_everything(self):
        self.assertEqual(rank(preference(locations=[], categories=[], keywords=[""]), [None, {}, item()]), [])
        self.assertEqual(rank(preference(), [None, {}]), [])


if __name__ == "__main__":
    unittest.main()
