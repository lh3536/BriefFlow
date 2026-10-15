import unittest
from unittest.mock import patch

from backend.retrieval.dates import extract_deadline
from backend.retrieval.sources import (
    fetch_tiaozhanbei,
    parse_cffex,
    parse_cffex_detail,
    parse_tiaozhanbei,
    parse_tiaozhanbei_detail,
)


class DeadlineTest(unittest.TestCase):
    def test_full_chinese_date(self):
        self.assertEqual(extract_deadline("报名截止日期：2026年5月20日。"), "2026-05-20")

    def test_iso_date(self):
        self.assertEqual(extract_deadline("报名截止 2026-10-31"), "2026-10-31")

    def test_no_year_is_empty(self):
        self.assertEqual(extract_deadline("报名截止到10月20日"), "")

    def test_no_keyword_is_empty(self):
        self.assertEqual(extract_deadline("欢迎大家报名参加本次竞赛"), "")

    def test_multiple_dates_is_empty(self):
        self.assertEqual(extract_deadline("截止日期：2026年5月20日，初赛2026年6月1日"), "")

    def test_registration_window_is_explicit_deadline(self):
        self.assertEqual(extract_deadline("报名时间：即日起至2026年10月31日"), "2026-10-31")


class TiaozhanbeiTest(unittest.TestCase):
    def test_parse_links_and_ignores_external(self):
        html = (
            '<a href="/article/15842/">挑战杯通知一</a>'
            '<a href="/article/15841/">挑战杯通知二</a>'
            '<a href="https://mp.weixin.qq.com/s/xxx">外部链接</a>'
        )
        items = parse_tiaozhanbei(html)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["category"], "竞赛")
        self.assertEqual(items[0]["source_url"], "https://www.tiaozhanbei.net/article/15842/")
        self.assertEqual(items[0]["organization"], "挑战杯官网")

    def test_detail_enrichment_keeps_unknown_location(self):
        item = parse_tiaozhanbei('<a href="/article/15842/">列表标题</a>')[0]
        html = """
        <html><head><title>挑战杯正式通知</title><script>ignore me</script></head>
        <body><p>发表于 2026.05.23</p><p>报名截止：2026年6月30日。</p><p>详情正文。</p></body></html>
        """
        enriched = parse_tiaozhanbei_detail(html, item)
        self.assertEqual(enriched["location"], "未注明")
        self.assertEqual(enriched["published_at"], "2026-05-23")
        self.assertEqual(enriched["deadline"], "2026-06-30")
        self.assertIn("详情正文", enriched["summary"])
        self.assertNotIn("ignore me", enriched["summary"])

    def test_detail_failure_keeps_list_item_and_batch_continues(self):
        listing = "".join(
            f'<a href="/article/{article_id}/">通知{article_id}</a>'
            for article_id in (1, 2, 3)
        )
        detail = "<html><title>详情</title><body>报名截止：2026年6月30日。</body></html>"
        with (
            patch("backend.retrieval.sources._fetch_html", side_effect=[listing, detail, OSError("offline"), detail]),
            patch("backend.retrieval.sources.sleep") as delay,
            self.assertLogs("backend.retrieval.sources", level="WARNING") as logs,
        ):
            items = fetch_tiaozhanbei()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["deadline"], "2026-06-30")
        self.assertEqual(items[1]["title"], "通知2")
        self.assertEqual(items[2]["deadline"], "2026-06-30")
        self.assertEqual(delay.call_count, 2)
        self.assertTrue(any("detail_failed" in message for message in logs.output))


class CffexTest(unittest.TestCase):
    def test_parse_filters_relevant_competitions(self):
        html = (
            '<a class="list_a_text " href="/cn/jysdt/20260807/48440.html" title="第十二届中金所杯全国大学生金融知识大赛正式启动">中金所杯</a>'
            ' <a class="time comparetime">2026-08-07</a>'
            '<a class="list_a_text " href="/cn/jysdt/20260714/48260.html" title="西安交大与中国金融期货交易所签署合作备忘录">合作</a>'
            ' <a class="time comparetime">2026-07-14</a>'
        )
        items = parse_cffex(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["published_at"], "2026-08-07")
        self.assertEqual(items[0]["category"], "竞赛")
        self.assertEqual(items[0]["source_url"], "http://www.cffex.com.cn/cn/jysdt/20260807/48440.html")

    def test_detail_enrichment_extracts_registration_deadline(self):
        item = parse_cffex(
            '<a href="/cn/jysdt/20260807/48440.html" title="中金所杯大学生金融知识大赛">中金所杯</a>'
            ' <a class="time comparetime">2026-08-07</a>'
        )[0]
        html = """
        <html><head><title>中金所杯大学生金融知识大赛| 中国金融期货交易所</title></head>
        <body><p>报名时间：即日起至2026年10月31日</p><p>普通高校全日制在校大学生可参加。</p></body></html>
        """
        enriched = parse_cffex_detail(html, item)
        self.assertEqual(enriched["title"], "中金所杯大学生金融知识大赛")
        self.assertEqual(enriched["deadline"], "2026-10-31")
        self.assertIn("全日制在校大学生", enriched["summary"])


if __name__ == "__main__":
    unittest.main()
