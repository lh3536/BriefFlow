import unittest

from backend.retrieval.dates import extract_deadline
from backend.retrieval.sources import parse_cffex, parse_tiaozhanbei


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


class TiaozhanbeiTest(unittest.TestCase):
    def test_parse_links_and_ignores_external(self):
        html = (
            '<a href="/article/15842/">挑战杯通知一</a>'
            '<a href="/article/15841/">挑战杯通知二</a>'
            '<a href="https://mp.weixin.qq.com/s/xxx">外部链接</a>'
        )
        items = parse_tiaozhanbei(html)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["category"], "经管比赛")
        self.assertEqual(items[0]["source_url"], "https://www.tiaozhanbei.net/article/15842/")
        self.assertEqual(items[0]["organization"], "挑战杯官网")


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
        self.assertEqual(items[0]["category"], "经管比赛")
        self.assertEqual(items[0]["source_url"], "http://www.cffex.com.cn/cn/jysdt/20260807/48440.html")


if __name__ == "__main__":
    unittest.main()
