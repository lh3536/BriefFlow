"""Bounded adapters for the approved public Retrieval sources."""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from time import sleep
from typing import ClassVar
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from backend.retrieval.dates import extract_deadline

UKRI_URL = "https://www.ukri.org/opportunity/feed/"
UKRI_SOURCE = "UK Research and Innovation (UKRI)"
TIAOZHANBEI_URL = "https://www.tiaozhanbei.net/tzb"
TIAOZHANBEI_SOURCE = "挑战杯官网"
CFFEX_URL = "http://www.cffex.com.cn/cn/jysdt.html"
CFFEX_SOURCE = "中国金融期货交易所"
HKEX_URL = "https://www.hkexgroup.com/About-HKEX/Careers-at-HKEX/Early-Careers?sc_lang=en"
HKEX_SOURCE = "香港交易所"
MACAO_GCS_URL = "https://govinfohub.gcs.gov.mo/api/rss/n/zh-hans"
MACAO_GCS_SOURCE = "澳门特别行政区政府新闻局"
SFC_SOURCE = "香港证券及期货事务监察委员会"
SFC_URLS = (
    (
        (
            "https://www.sfc.hk/en/Career/Why-the-SFC/Join-us-as-an-Intern/"
            "Summer-and-Winter-Internship-Programme"
        ),
        "SFC Summer and Winter Internship Programme",
    ),
    (
        (
            "https://www.sfc.hk/en/Career/Why-the-SFC/Join-us-as-an-Intern/"
            "Sustainable-Finance-Internship-Programme"
        ),
        "SFC Sustainable Finance Internship Programme",
    ),
)
MAX_BYTES = 2_000_000
MAX_ITEMS = 20
MAX_DETAIL_ITEMS = 3
DETAIL_DELAY_SECONDS = 1.0
MACAO_GCS_DELAY_SECONDS = 20.0
LOCAL_TIMEZONE = timezone(timedelta(hours=8))

WEB_SOURCES = [
    UKRI_SOURCE, TIAOZHANBEI_SOURCE, CFFEX_SOURCE,
    HKEX_SOURCE, MACAO_GCS_SOURCE, SFC_SOURCE,
]


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class _VisiblePageText(HTMLParser):
    """Extract visible text and title from one already-approved detail page."""

    _IGNORED: ClassVar[set[str]] = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.title_parts = []
        self._ignored_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self._IGNORED:
            self._ignored_depth += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self._IGNORED and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._ignored_depth:
            return
        self.parts.append(data)
        if self._in_title:
            self.title_parts.append(data)


def _plain_page(html: str) -> tuple[str, str]:
    parser = _VisiblePageText()
    parser.feed(html)
    title = " ".join(" ".join(parser.title_parts).split())
    text = "\n".join(part.strip() for part in parser.parts if part.strip())
    return title, text


def _fetch_html(url: str, expected_host: str) -> str:
    request = Request(url, headers={"User-Agent": "BriefFlow/0.1 public reader", "Accept": "text/html"})
    with urlopen(request, timeout=15) as response:
        if urlsplit(response.url).hostname != expected_host:
            raise ValueError("Unexpected source redirect")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Response exceeds size limit")
    return payload.decode("utf-8", errors="replace")


def _fetch_bytes(url: str, expected_host: str, accept: str) -> bytes:
    request = Request(url, headers={"User-Agent": "BriefFlow/0.1 public reader", "Accept": accept})
    with urlopen(request, timeout=15) as response:
        if urlsplit(response.url).hostname != expected_host:
            raise ValueError("Unexpected source redirect")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Response exceeds size limit")
    return payload


def _today() -> date:
    return datetime.now(LOCAL_TIMEZONE).date()


def _is_open(deadline: str, as_of: date | None) -> bool:
    try:
        return bool(deadline) and date.fromisoformat(deadline) >= (as_of or _today())
    except ValueError:
        return False


def parse_tiaozhanbei_detail(html: str, item: dict) -> dict:
    """Enrich one challenge-cup list record with detail-page evidence."""
    page_title, text = _plain_page(html)
    published = item.get("published_at", "")
    match = re.search(r"发表于\s*(\d{4})[.年/-](\d{1,2})[.月/-](\d{1,2})日?", text)
    if match:
        published = f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    return {
        **item,
        "title": page_title or item["title"],
        "summary": text[:12_000] or item["summary"],
        "published_at": published,
        "deadline": extract_deadline(text),
    }


def parse_cffex_detail(html: str, item: dict) -> dict:
    """Enrich one CFFEX list record without inventing source attributes."""
    page_title, text = _plain_page(html)
    clean_title = page_title.split("|")[0].strip() if page_title else item["title"]
    return {
        **item,
        "title": clean_title,
        "summary": text[:12_000] or item["summary"],
        "deadline": extract_deadline(text),
    }


def _enrich_details(items: list[dict], parser, expected_host: str) -> list[dict]:
    enriched = []
    for index, item in enumerate(items):
        if index >= MAX_DETAIL_ITEMS:
            enriched.append(item)
            continue
        if index:
            sleep(DETAIL_DELAY_SECONDS)
        try:
            enriched.append(parser(_fetch_html(item["source_url"], expected_host), item))
        except (OSError, ValueError) as exc:
            logging.getLogger(__name__).warning(
                "detail_failed source=%s url=%s reason=%s",
                item["source"], item["source_url"], type(exc).__name__,
            )
            enriched.append(item)
    return enriched


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
            "location": "未注明", "category": "科研",
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
    for path, title in re.findall(r'<a\b[^>]*href="(/article/\d+/)">(.*?)</a>', html, re.DOTALL):
        title = " ".join(title.split())
        if not title:
            continue
        items.append({
            "title": title, "organization": TIAOZHANBEI_SOURCE, "location": "未注明",
            "category": "竞赛", "summary": title, "source": TIAOZHANBEI_SOURCE,
            "source_url": "https://www.tiaozhanbei.net" + path,
            "published_at": "", "deadline": "", "tags": ["竞赛", "挑战杯"], "requirements": [],
        })
        if len(items) >= MAX_ITEMS:
            break
    return items


def fetch_tiaozhanbei() -> list[dict]:
    """挑战杯列表 + 最多三个详情页；全国性赛事不伪造单一城市。"""
    items = parse_tiaozhanbei(_fetch_html(TIAOZHANBEI_URL, "www.tiaozhanbei.net"))
    return _enrich_details(items, parse_tiaozhanbei_detail, "www.tiaozhanbei.net")


def parse_cffex(html: str) -> list[dict]:
    items = []
    for path, title, date_str in re.findall(
        r'<a[^>]*href="(/cn/jysdt/\d{8}/\d+\.html)"[^>]*title="([^"]*)"[^>]*>.*?</a>'
        r'\s*<a[^>]*class="time[^"]*"[^>]*>(\d{4}-\d{2}-\d{2})</a>',
        html, re.DOTALL,
    ):
        title = " ".join(title.split())
        if not title or not any(k in title for k in ("中金所杯", "大学生", "金融知识大赛", "辩论赛")):
            continue
        items.append({
            "title": title, "organization": CFFEX_SOURCE, "location": "未注明",
            "category": "竞赛", "summary": title, "source": CFFEX_SOURCE,
            "source_url": "http://www.cffex.com.cn" + path,
            "published_at": date_str, "deadline": "", "tags": ["竞赛", "金融"], "requirements": [],
        })
        if len(items) >= MAX_ITEMS:
            break
    return items


def fetch_cffex() -> list[dict]:
    """中金所相关竞赛列表 + 最多三个详情页。"""
    items = parse_cffex(_fetch_html(CFFEX_URL, "www.cffex.com.cn"))
    return _enrich_details(items, parse_cffex_detail, "www.cffex.com.cn")


def parse_hkex(html: str, *, as_of: date | None = None) -> list[dict]:
    """Extract only the current HKEX Summer Internship tab from the shared page."""
    _, text = _plain_page(html)
    start = text.find("Starting in mid-June")
    end = text.find("Successful interns", start)
    if start < 0 or end < 0:
        return []
    section = text[start:end].strip()
    deadline = extract_deadline(section)
    if not _is_open(deadline, as_of):
        return []
    return [{
        "title": "HKEX Summer Internship Programme", "organization": HKEX_SOURCE,
        "location": "香港", "category": "实习", "summary": section[:12_000],
        "source": HKEX_SOURCE, "source_url": HKEX_URL, "published_at": "",
        "deadline": deadline, "tags": ["香港", "金融", "实习"], "requirements": [],
    }]


def fetch_hkex() -> list[dict]:
    return parse_hkex(_fetch_html(HKEX_URL, "www.hkexgroup.com"))


def _rss_date(raw_date: str) -> str:
    if not raw_date:
        return ""
    try:
        return parsedate_to_datetime(raw_date).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", raw_date)
        if not match:
            return ""
        try:
            return date(*(int(part) for part in match.groups())).isoformat()
        except ValueError:
            return ""


def parse_macao_gcs_feed(payload: bytes) -> list[dict]:
    """Select university/youth competitions from the official Macao news RSS."""
    if len(payload) > MAX_BYTES or b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("RSS exceeds size limit or contains unsupported declarations")
    root = ET.fromstring(payload)
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("Expected an RSS channel")
    items = []
    for entry in root.findall("./channel/item"):
        title = " ".join((entry.findtext("title") or "").split())
        url = (entry.findtext("link") or "").strip()
        parts = urlsplit(url)
        if not any(word in title for word in ("比赛", "比賽", "竞赛", "競賽")):
            continue
        if not any(word in title for word in ("大学", "大专", "高校", "青年", "學生", "学生", "教青局")):
            continue
        if parts.scheme != "https" or parts.hostname != "www.gcs.gov.mo" or not parts.path.startswith("/detail/zh-hans/"):
            continue
        items.append({
            "title": title, "organization": MACAO_GCS_SOURCE, "location": "澳门",
            "category": "竞赛", "summary": title, "source": MACAO_GCS_SOURCE,
            "source_url": url, "published_at": _rss_date(entry.findtext("pubDate", "")),
            "deadline": "", "tags": ["澳门", "竞赛"], "requirements": [],
        })
        if len(items) >= MAX_DETAIL_ITEMS:
            break
    return items


def _macao_deadline(text: str, published_at: str) -> str:
    direct = extract_deadline(text)
    if direct:
        return direct
    registration = re.search(
        r"即日起至\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日[^。；;\n]{0,40}?报名",
        text,
    )
    if registration:
        try:
            return date(*(int(part) for part in registration.groups())).isoformat()
        except ValueError:
            return ""
    try:
        published = date.fromisoformat(published_at)
    except ValueError:
        return ""
    for segment in re.split(r"[。；;！!\n]+", text):
        if not any(hint in segment for hint in ("截止", "截至", "报名期", "報名期", "征件期")):
            continue
        tokens = set(re.findall(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", segment))
        if len(tokens) != 1:
            return ""
        month, day = next(iter(tokens))
        try:
            inferred = date(published.year, int(month), int(day))
        except ValueError:
            return ""
        return inferred.isoformat() if inferred >= published else ""
    return ""


def parse_macao_gcs_detail(html: str, item: dict, *, as_of: date | None = None) -> dict | None:
    _, text = _plain_page(html)
    deadline = _macao_deadline(text, item.get("published_at", ""))
    if not _is_open(deadline, as_of):
        return None
    return {**item, "summary": text[:12_000] or item["summary"], "deadline": deadline}


def fetch_macao_gcs() -> list[dict]:
    payload = _fetch_bytes(MACAO_GCS_URL, "govinfohub.gcs.gov.mo", "application/rss+xml, application/xml, text/xml")
    candidates = parse_macao_gcs_feed(payload)
    items = []
    for candidate in candidates:
        sleep(MACAO_GCS_DELAY_SECONDS)
        try:
            item = parse_macao_gcs_detail(
                _fetch_html(candidate["source_url"], "www.gcs.gov.mo"), candidate,
            )
        except (OSError, ValueError) as exc:
            logging.getLogger(__name__).warning(
                "detail_failed source=%s url=%s reason=%s",
                candidate["source"], candidate["source_url"], type(exc).__name__,
            )
            continue
        if item is not None:
            items.append(item)
    return items


def parse_sfc_detail(html: str, title: str, url: str, *, as_of: date | None = None) -> dict | None:
    _, text = _plain_page(html)
    deadline = extract_deadline(text)
    if not _is_open(deadline, as_of):
        return None
    return {
        "title": title, "organization": SFC_SOURCE, "location": "香港",
        "category": "实习", "summary": text[:12_000], "source": SFC_SOURCE,
        "source_url": url, "published_at": "", "deadline": deadline,
        "tags": ["香港", "金融", "监管", "实习"], "requirements": [],
    }


def fetch_sfc() -> list[dict]:
    items = []
    for index, (url, title) in enumerate(SFC_URLS):
        if index:
            sleep(DETAIL_DELAY_SECONDS)
        try:
            item = parse_sfc_detail(_fetch_html(url, "www.sfc.hk"), title, url)
        except (OSError, ValueError) as exc:
            logging.getLogger(__name__).warning(
                "detail_failed source=%s url=%s reason=%s", SFC_SOURCE, url, type(exc).__name__,
            )
            continue
        if item is not None:
            items.append(item)
    return items


def fetch_web() -> list[dict]:
    """合并所有公开来源；单源失败不影响其他来源。"""
    items = []
    for name, fetch in (
        ("ukri", fetch_ukri), ("tiaozhanbei", fetch_tiaozhanbei), ("cffex", fetch_cffex),
        ("hkex", fetch_hkex), ("macao_gcs", fetch_macao_gcs), ("sfc", fetch_sfc),
    ):
        try:
            items.extend(fetch())
        except (OSError, ValueError, ET.ParseError):
            logging.getLogger(__name__).warning("source_failed source=%s", name)
    return items
