"""One public source: UKRI's official funding-opportunity RSS, no page crawling."""
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import logging
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

UKRI_URL = "https://www.ukri.org/opportunity/feed/"
UKRI_SOURCE = "UK Research and Innovation (UKRI)"
TIAOZHANBEI_URL = "https://www.tiaozhanbei.net/tzb"
TIAOZHANBEI_SOURCE = "挑战杯官网"
CFFEX_URL = "http://www.cffex.com.cn/cn/jysdt.html"
CFFEX_SOURCE = "中国金融期货交易所"
MAX_BYTES = 2_000_000
MAX_ITEMS = 20

WEB_SOURCES = [UKRI_SOURCE, TIAOZHANBEI_SOURCE, CFFEX_SOURCE]


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def parse_ukri_feed(payload: bytes) -> list[dict]:
    """Adapt RSS names to canonical fields; absent eligibility/dates stay unknown."""
    if len(payload) > MAX_BYTES or b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("RSS exceeds size limit or contains unsupported declarations")
    root = ET.fromstring(payload)
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("Expected an RSS channel")
    items = []
    for entry in root.findall("./channel/item")[:MAX_ITEMS]:
        parser = _PlainText()
        parser.feed(entry.findtext("description", ""))
        published = ""
        raw_date = entry.findtext("pubDate", "")
        if raw_date:
            try:
                published = parsedate_to_datetime(raw_date).date().isoformat()
            except (ValueError, TypeError, OverflowError):
                published = raw_date
        items.append({
            "title": entry.findtext("title", ""), "organization": UKRI_SOURCE,
            "location": "未注明", "category": "科研机会",
            "summary": " ".join(" ".join(parser.parts).split()),
            "source": UKRI_SOURCE, "source_url": entry.findtext("link", ""),
            "published_at": published, "deadline": "", "tags": ["科研资助", "UKRI"],
            "requirements": [],
        })
    return items


def fetch_ukri() -> list[dict]:
    """One bounded GET per call. No authentication, retries, paging or scraping."""
    request = Request(UKRI_URL, headers={"User-Agent": "BriefFlow/0.1 public RSS reader", "Accept": "application/rss+xml, application/xml, text/xml"})
    with urlopen(request, timeout=15) as response:
        if urlsplit(response.url).hostname != "www.ukri.org":
            raise ValueError("Unexpected source redirect")
        payload = response.read(MAX_BYTES + 1)
    return parse_ukri_feed(payload)


def parse_tiaozhanbei(html: str) -> list[dict]:
    items = []
    for path, title in re.findall(r'<a\b[^>]*href="(/article/\d+/)">(.*?)</a>', html, re.S):
        title = " ".join(title.split())
        if not title:
            continue
        items.append({
            "title": title, "organization": TIAOZHANBEI_SOURCE, "location": "未注明",
            "category": "经管比赛", "summary": title, "source": TIAOZHANBEI_SOURCE,
            "source_url": "https://www.tiaozhanbei.net" + path,
            "published_at": "", "deadline": "", "tags": ["竞赛", "挑战杯"], "requirements": [],
        })
        if len(items) >= MAX_ITEMS:
            break
    return items


def fetch_tiaozhanbei() -> list[dict]:
    """挑战杯官网「挑战杯动态」列表 → 经管比赛条目（全国性，无单一城市）。"""
    request = Request(TIAOZHANBEI_URL, headers={"User-Agent": "BriefFlow/0.1 public reader", "Accept": "text/html"})
    with urlopen(request, timeout=15) as response:
        if urlsplit(response.url).hostname != "www.tiaozhanbei.net":
            raise ValueError("Unexpected source redirect")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Response exceeds size limit")
    return parse_tiaozhanbei(payload.decode("utf-8", errors="replace"))


def parse_cffex(html: str) -> list[dict]:
    items = []
    for path, title, date_str in re.findall(
        r'<a[^>]*href="(/cn/jysdt/\d{8}/\d+\.html)"[^>]*title="([^"]*)"[^>]*>.*?</a>'
        r'\s*<a[^>]*class="time[^"]*"[^>]*>(\d{4}-\d{2}-\d{2})</a>',
        html, re.S,
    ):
        title = " ".join(title.split())
        if not title or not any(k in title for k in ("中金所杯", "大学生", "金融知识大赛", "辩论赛")):
            continue
        items.append({
            "title": title, "organization": CFFEX_SOURCE, "location": "未注明",
            "category": "经管比赛", "summary": title, "source": CFFEX_SOURCE,
            "source_url": "http://www.cffex.com.cn" + path,
            "published_at": date_str, "deadline": "", "tags": ["竞赛", "金融"], "requirements": [],
        })
        if len(items) >= MAX_ITEMS:
            break
    return items


def fetch_cffex() -> list[dict]:
    """中金所「交易所动态」里的大学生竞赛（中金所杯等）→ 经管比赛条目。"""
    request = Request(CFFEX_URL, headers={"User-Agent": "BriefFlow/0.1 public reader", "Accept": "text/html"})
    with urlopen(request, timeout=15) as response:
        if urlsplit(response.url).hostname != "www.cffex.com.cn":
            raise ValueError("Unexpected source redirect")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Response exceeds size limit")
    return parse_cffex(payload.decode("utf-8", errors="replace"))


def fetch_web() -> list[dict]:
    """合并所有公开来源；单源失败不影响其他来源。"""
    items = []
    for name, fetch in (("ukri", fetch_ukri), ("tiaozhanbei", fetch_tiaozhanbei), ("cffex", fetch_cffex)):
        try:
            items.extend(fetch())
        except (OSError, ValueError, ET.ParseError):
            logging.getLogger(__name__).warning("source_failed source=%s", name)
    return items
