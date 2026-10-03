"""One public source: UKRI's official funding-opportunity RSS, no page crawling."""
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

UKRI_URL = "https://www.ukri.org/opportunity/feed/"
UKRI_SOURCE = "UK Research and Innovation (UKRI)"
MAX_BYTES = 2_000_000
MAX_ITEMS = 20


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
