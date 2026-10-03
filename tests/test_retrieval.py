"""Offline retrieval/database behavior; all network calls are mocked in tests."""
from copy import deepcopy
from contextlib import closing
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from backend.retrieval.database import load_items, save_items
from backend.retrieval.schema import FIELDS, canonical_url, normalize_item, validate_item
from backend.retrieval.service import MOCK_PATH, clean_items, get_items
from backend.retrieval.sources import MAX_BYTES, UKRI_SOURCE, fetch_ukri, parse_ukri_feed
from backend.router.service import run_brief_flow

FIXTURE = Path(__file__).parent / "fixtures" / "ukri_excerpt.xml"


def record(**changes):
    return {
        "title": "Research funding", "organization": "Example Institute",
        "source": "Test Fixture", "source_url": "https://example.com/opportunity/1",
        "location": "未注明", "category": "科研机会", "summary": "Test only",
        "published_at": "2026-10-01", "deadline": "", "tags": ["research"],
        "requirements": [], "last_updated": "2026-10-03T00:00:00+00:00", **changes,
    }


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "items.sqlite3"
        environment = patch.dict(os.environ, {
            "BRIEFFLOW_RETRIEVAL_MODE": "mock", "BRIEFFLOW_DB_PATH": str(self.db),
        })
        environment.start()
        self.addCleanup(environment.stop)

    def test_mock_still_reads_without_network_or_database(self):
        before = MOCK_PATH.read_bytes()
        with patch("backend.retrieval.service.fetch_ukri") as fetch:
            items = get_items({})
        fetch.assert_not_called()
        self.assertEqual(len(items), 15)
        self.assertEqual(items[0]["job_id"], "job_001")
        self.assertEqual(items[0]["source"], "BriefFlow Mock")
        self.assertEqual(MOCK_PATH.read_bytes(), before)
        self.assertFalse(self.db.exists())

    def test_normalize_schema_and_discard_source_scores(self):
        raw = record(match_score=99, why_recommended=["untrusted source score"], odd_vendor_key=1)
        before = deepcopy(raw)
        item = normalize_item(raw)
        self.assertEqual(set(item), set(FIELDS))
        self.assertEqual(validate_item(item), [])
        self.assertEqual(raw, before)
        self.assertEqual(item["item_id"], normalize_item(raw)["item_id"])

    def test_mock_field_mapping(self):
        raw = json.loads(MOCK_PATH.read_text(encoding="utf-8"))[0]
        item = normalize_item({**raw, "source": "BriefFlow Mock"})
        self.assertEqual(item["organization"], raw["company"])
        self.assertEqual(item["source_url"], raw["link"])
        self.assertEqual(item["item_id"], raw["job_id"])

    def test_url_normalization(self):
        self.assertEqual(canonical_url("https://EXAMPLE.com:443/a?b=2&utm_source=demo&a=1#section"), "https://example.com/a?a=1&b=2")
        self.assertEqual(canonical_url("https://example.com:80/a"), "https://example.com:80/a")

    def test_invalid_url_is_rejected(self):
        for url in ("", "javascript:alert(1)", "https://user:password@example.com/a", "http://127.0.0.1/a", "https://bad host/a", "https://example.com:bad/a"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    normalize_item(record(source_url=url))

    def test_duplicates_by_url_and_content(self):
        raw = [record(), record(title="Changed title", source_url="https://example.com/opportunity/1?utm_source=a#x"), record(source_url="https://example.com/other")]
        items, rejected, duplicates = clean_items(raw)
        self.assertEqual((len(items), rejected, duplicates), (1, 0, 2))

    def test_different_deadlines_remain_distinct(self):
        items, rejected, duplicates = clean_items([record(), record(source_url="https://example.com/2", deadline="2026-12-01")])
        self.assertEqual((len(items), rejected, duplicates), (2, 0, 0))

    def test_invalid_records_skip_without_losing_valid_record(self):
        invalid = [None, {}, record(title=""), record(source=""), record(category="unknown"), record(location=[]), record(location="<html>"), record(deadline="2026-02-30"), record(tags="research")]
        with self.assertLogs("backend.retrieval.service", level="WARNING") as logs:
            items, rejected, duplicates = clean_items([*invalid, record()])
        self.assertEqual((len(items), rejected, duplicates), (1, len(invalid), 0))
        self.assertTrue(all("reason=" in message for message in logs.output))

    def test_sqlite_round_trip_without_ranking_columns(self):
        item = normalize_item(record())
        self.assertEqual(save_items([item], self.db), 1)
        self.assertEqual(load_items(self.db), [item])
        with closing(sqlite3.connect(self.db)) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(items)")}
        self.assertNotIn("match_score", columns)
        self.assertNotIn("why_recommended", columns)

    def test_sqlite_upsert_and_cross_batch_deduplication(self):
        save_items([record()], self.db)
        self.assertEqual(save_items([record(summary="Updated")], self.db), 1)
        with self.assertLogs("backend.retrieval.database", level="WARNING"):
            self.assertEqual(save_items([record(source_url="https://example.com/duplicate")], self.db), 0)
        items = load_items(self.db)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["summary"], "Updated")

    def test_sqlite_skips_invalid_record(self):
        with self.assertLogs("backend.retrieval.database", level="WARNING"):
            self.assertEqual(save_items([record(title=""), record()], self.db), 1)
        self.assertEqual(len(load_items(self.db)), 1)

    def test_database_mode_and_legacy_aliases(self):
        save_items([record()], self.db)
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "database"}):
            items = get_items({})
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["job_id"], item["item_id"])
        self.assertEqual(item["company"], item["organization"])
        self.assertEqual(item["link"], item["source_url"])
        self.assertEqual((item["match_score"], item["why_recommended"]), (0, []))
        self.assertEqual(json.loads(json.dumps(items, allow_nan=False)), items)

    def test_empty_database_falls_back_to_mock(self):
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "database"}), self.assertLogs("backend.retrieval.service", level="WARNING") as logs:
            self.assertEqual(len(get_items({})), 15)
        self.assertTrue(any("fallback=mock" in message for message in logs.output))

    def test_corrupt_database_falls_back(self):
        self.db.write_bytes(b"not a database")
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "database"}), self.assertLogs("backend.retrieval.service", level="WARNING"):
            self.assertEqual(len(get_items({})), 15)

    def test_corrupt_row_skipped_and_counted(self):
        save_items([record(), record(title="Other", source_url="https://example.com/2")], self.db)
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE items SET tags = 'broken JSON' WHERE title = 'Other'")
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "database"}), self.assertLogs("backend.retrieval", level="INFO") as logs:
            self.assertEqual(len(get_items({})), 1)
        metrics = [json.loads(line.split("retrieval ", 1)[1]) for line in logs.output if "retrieval {" in line][0]
        self.assertEqual((metrics["items_fetched"], metrics["items_rejected"]), (2, 1))

    def test_real_feed_fixture_normalizes(self):
        raw = parse_ukri_feed(FIXTURE.read_bytes())
        items, rejected, duplicates = clean_items(raw)
        self.assertEqual((len(items), rejected, duplicates), (2, 0, 0))
        self.assertEqual(items[0]["source"], UKRI_SOURCE)
        self.assertEqual(items[0]["published_at"], "2026-10-02")
        self.assertEqual(items[0]["location"], "未注明")
        self.assertEqual(items[0]["deadline"], "")

    def test_rss_html_and_invalid_date(self):
        xml = b'<rss><channel><item><title>Test</title><link>https://example.com/a</link><description>&lt;p&gt;Funding &amp;amp; research&lt;/p&gt;</description><pubDate>invalid</pubDate></item></channel></rss>'
        raw = parse_ukri_feed(xml)
        self.assertEqual(raw[0]["summary"], "Funding & research")
        with self.assertLogs("backend.retrieval.service", level="WARNING"):
            self.assertEqual(clean_items(raw)[1], 1)

    def test_rss_limits_and_wrong_format(self):
        for payload in (b"x" * (MAX_BYTES + 1), b'<!DOCTYPE rss><rss><channel/></rss>', b'<html/>'):
            with self.subTest(payload_length=len(payload)):
                with self.assertRaises(ValueError):
                    parse_ukri_feed(payload)

    def test_fetch_uses_bounded_public_request(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.url = "https://www.ukri.org/opportunity/feed/"
        response.read.return_value = FIXTURE.read_bytes()
        with patch("backend.retrieval.sources.urlopen", return_value=response) as open_url:
            self.assertEqual(len(fetch_ukri()), 2)
        self.assertEqual(open_url.call_args.kwargs["timeout"], 15)
        response.read.assert_called_once_with(MAX_BYTES + 1)

    def test_web_mode_caches_valid_items(self):
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "web"}), patch("backend.retrieval.service.fetch_ukri", return_value=parse_ukri_feed(FIXTURE.read_bytes())):
            items = get_items({})
        self.assertEqual(len(items), 2)
        self.assertEqual(len(load_items(self.db)), 2)
        self.assertTrue(all(item["source"] == UKRI_SOURCE for item in items))

    def test_network_failure_falls_back_and_pipeline_runs(self):
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "web"}), patch("backend.retrieval.service.fetch_ukri", side_effect=URLError("offline")), self.assertLogs("backend.retrieval.service", level="INFO") as logs:
            result = run_brief_flow("广州金融实习，不要销售岗")
        self.assertGreater(result["total_items"], 0)
        self.assertTrue(all(item["source"] == "BriefFlow Mock" for item in result["recommended_items"]))
        self.assertTrue(any("fallback=mock" in message for message in logs.output))
        self.assertFalse(self.db.exists())

    def test_empty_web_falls_back(self):
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "web"}), patch("backend.retrieval.service.fetch_ukri", return_value=[]), self.assertLogs("backend.retrieval.service", level="WARNING"):
            self.assertEqual(len(get_items({})), 15)

    def test_incomplete_response_and_invalid_xml_fall_back(self):
        import xml.etree.ElementTree as ET
        for error in (IncompleteRead(b"partial"), ET.ParseError("invalid XML")):
            with self.subTest(error=type(error).__name__), patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "web"}), patch("backend.retrieval.service.fetch_ukri", side_effect=error), self.assertLogs("backend.retrieval.service", level="WARNING"):
                self.assertEqual(len(get_items({})), 15)

    def test_cache_failure_does_not_discard_web_results(self):
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "web"}), patch("backend.retrieval.service.fetch_ukri", return_value=[record()]), patch("backend.retrieval.service.save_items", side_effect=sqlite3.OperationalError("read only")), self.assertLogs("backend.retrieval.service", level="WARNING"):
            self.assertEqual(get_items({})[0]["source"], "Test Fixture")

    def test_metrics_counts_and_duration(self):
        raw = [record(), record(), record(title="")]
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "web"}), patch("backend.retrieval.service.fetch_ukri", return_value=raw), self.assertLogs("backend.retrieval.service", level="INFO") as logs:
            self.assertEqual(len(get_items({})), 1)
        metrics = json.loads(next(line.split("retrieval ", 1)[1] for line in logs.output if "retrieval {" in line))
        self.assertEqual((metrics["items_fetched"], metrics["items_accepted"], metrics["items_rejected"], metrics["duplicates_removed"]), (3, 1, 1, 1))
        self.assertIn("source", metrics)
        self.assertGreaterEqual(metrics["duration"], 0)

    def test_missing_mock_returns_empty_without_crash(self):
        with patch("backend.retrieval.service.MOCK_PATH", Path(self.temp.name) / "missing.json"), self.assertLogs("backend.retrieval.service", level="WARNING"):
            self.assertEqual(get_items({}), [])

    def test_unknown_mode_uses_mock(self):
        with patch.dict(os.environ, {"BRIEFFLOW_RETRIEVAL_MODE": "typo"}), self.assertLogs("backend.retrieval.service", level="WARNING"):
            self.assertEqual(len(get_items({})), 15)


if __name__ == "__main__":
    unittest.main()
