import unittest
from datetime import date

from backend.retrieval.dates import extract_deadline
from backend.retrieval.sources import (
    HKEX_URL,
    MACAO_GCS_SOURCE,
    parse_hkex,
    parse_macao_gcs_detail,
    parse_macao_gcs_feed,
    parse_sfc_detail,
)


class D10DeadlineTest(unittest.TestCase):
    def test_english_deadline_phrases(self):
        self.assertEqual(
            extract_deadline("Applications are now open until 25 October 2026"),
            "2026-10-25",
        )
        self.assertEqual(
            extract_deadline("Applications must be submitted on or before 11 October 2026"),
            "2026-10-11",
        )


class HkexSourceTest(unittest.TestCase):
    html = """<html><head><title>Early Careers</title></head><body>
    <p>Graduate Programme applications close on 1 September 2026.</p>
    <p>Starting in mid-June, the 10-week HKEX Summer Internship Programme begins.</p>
    <p>Penultimate-year students can work in Finance, Treasury, Markets and Listing.</p>
    <p>Applications are now open until 25 October 2026.</p>
    <p>Successful interns may receive a return offer.</p></body></html>"""

    def test_only_open_summer_section_is_emitted(self):
        items = parse_hkex(self.html, as_of=date(2026, 10, 14))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_url"], HKEX_URL)
        self.assertEqual(items[0]["location"], "香港")
        self.assertEqual(items[0]["category"], "实习")
        self.assertEqual(items[0]["deadline"], "2026-10-25")
        self.assertNotIn("Graduate Programme", items[0]["summary"])
        self.assertEqual(parse_hkex(self.html, as_of=date(2026, 10, 26)), [])


class MacaoGcsSourceTest(unittest.TestCase):
    feed = """<?xml version="1.0" encoding="UTF-8"?><rss><channel>
    <item><title>居民设计比赛</title><link>https://www.gcs.gov.mo/detail/zh-hans/adult</link><pubDate>2026-10-14</pubDate></item>
    <item><title>教青局举办短视频创作比赛</title><link>https://www.gcs.gov.mo/detail/zh-hans/student</link><pubDate>2026-10-13</pubDate></item>
    <item><title>青年比赛外站</title><link>https://example.com/bad</link><pubDate>2026-10-13</pubDate></item>
    </channel></rss>""".encode()

    def test_feed_filters_audience_and_host_then_detail_uses_source_year(self):
        candidates = parse_macao_gcs_feed(self.feed)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source"], MACAO_GCS_SOURCE)
        self.assertEqual(candidates[0]["published_at"], "2026-10-13")
        detail = """<html><title>比赛</title><body><p>活动面向澳门高校学生。</p>
        <p>学生可由即日起至2026年10月23日前在网上报名系统报名，并于2026年10月30日前上传作品。</p>
        </body></html>"""
        item = parse_macao_gcs_detail(detail, candidates[0], as_of=date(2026, 10, 14))
        self.assertIsNotNone(item)
        self.assertEqual(item["deadline"], "2026-10-23")
        self.assertIsNone(parse_macao_gcs_detail(detail, candidates[0], as_of=date(2026, 10, 24)))


class SfcSourceTest(unittest.TestCase):
    def test_expired_programme_is_not_emitted(self):
        html = """<html><title>Internship</title><body>
        <p>Finance and Economics students may apply.</p>
        <p>Applications must be submitted on or before 11 October 2026.</p>
        </body></html>"""
        url = "https://www.sfc.hk/en/Career/example"
        self.assertIsNotNone(parse_sfc_detail(html, "SFC Internship", url, as_of=date(2026, 10, 10)))
        self.assertIsNone(parse_sfc_detail(html, "SFC Internship", url, as_of=date(2026, 10, 14)))


if __name__ == "__main__":
    unittest.main()
