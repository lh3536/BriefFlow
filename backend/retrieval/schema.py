"""Canonical source records and a compatibility projection for the pipeline."""
from datetime import date, datetime, timezone
import hashlib
import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CATEGORIES = {"金融实习", "经管比赛", "夏令营", "科研机会"}
FIELDS = (
    "item_id", "title", "organization", "location", "category", "summary",
    "source", "source_url", "published_at", "deadline", "tags", "requirements", "last_updated",
)


def canonical_url(value: str) -> str:
    """Validate a public HTTP(S) URL; remove fragments and tracking parameters."""
    if not isinstance(value, str) or re.search(r"[\s<>]", value):
        raise ValueError("source_url must be an HTTP(S) URL without whitespace")
    parts = urlsplit(value)
    host = parts.hostname or ""
    if parts.scheme not in ("http", "https") or not host or parts.username or parts.password:
        raise ValueError("source_url requires a public host and no credentials")
    if "." not in host or host.endswith(".local") or host == "localhost":
        raise ValueError("source_url must use a public host")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("source_url cannot point to a private IP")
    port = parts.port
    default_port = 443 if parts.scheme == "https" else 80
    netloc = host.lower() + (f":{port}" if port and port != default_port else "")
    query = sorted((key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                   if not key.lower().startswith("utm_") and key.lower() not in ("fbclid", "gclid"))
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", urlencode(query), ""))


def _text(raw: dict, key: str, default: str = "") -> str:
    value = raw.get(key, default)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return " ".join(value.split())


def normalize_item(raw_item: dict) -> dict:
    """Map mock/canonical input into source-only fields; discard ranking scores."""
    if not isinstance(raw_item, dict):
        raise ValueError("item must be an object")
    raw = raw_item
    item = {key: _text(raw, key) for key in FIELDS if key not in ("tags", "requirements")}
    item["organization"] = _text(raw, "organization", raw.get("company", ""))
    item["source_url"] = canonical_url(_text(raw, "source_url", raw.get("link", "")))
    item["item_id"] = _text(raw, "item_id", raw.get("job_id", "")) or hashlib.sha256(item["source_url"].encode()).hexdigest()[:24]
    item["last_updated"] = item["last_updated"] or datetime.now(timezone.utc).isoformat()
    for key in ("tags", "requirements"):
        values = raw.get(key, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"{key} must be a list of strings")
        item[key] = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    return item


def validate_item(item: dict) -> list[str]:
    """Return rejection reasons; unknown dates are empty, never invented."""
    errors = []
    for key in ("item_id", "title", "organization", "source"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            errors.append(f"{key} is required")
    category = item.get("category")
    if not isinstance(category, str) or category not in CATEGORIES:
        errors.append("category is not supported")
    location = item.get("location")
    if not isinstance(location, str) or not 1 <= len(location.strip()) <= 100 or re.search(r"[<>\x00-\x1f]", location):
        errors.append("location must be a short plain-text label")
    try:
        canonical_url(item.get("source_url"))
    except (ValueError, TypeError):
        errors.append("source_url is invalid")
    for key in ("published_at", "deadline"):
        value = item.get(key, "")
        try:
            if value:
                date.fromisoformat(value)
        except (ValueError, TypeError):
            errors.append(f"{key} must be an ISO date or empty")
    try:
        datetime.fromisoformat(item.get("last_updated", "").replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        errors.append("last_updated must be an ISO timestamp")
    return errors


def content_key(item: dict) -> str:
    """Stable key for a title/organization/deadline combination."""
    parts = [" ".join(item[key].split()).casefold() for key in ("title", "organization", "deadline")]
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def deduplicate_items(items: list[dict]) -> tuple[list[dict], int]:
    """Keep the first record with each URL, content key and item ID."""
    urls, contents, ids = set(), set(), set()
    unique = []
    for item in items:
        url, key, item_id = item["source_url"], content_key(item), item["item_id"]
        if url in urls or key in contents or item_id in ids:
            continue
        urls.add(url)
        contents.add(key)
        ids.add(item_id)
        unique.append(item)
    return unique, len(items) - len(unique)


def to_pipeline_item(item: dict) -> dict:
    """Expose canonical metadata plus legacy keys expected by existing modules."""
    return {
        **item, "job_id": item["item_id"], "company": item["organization"],
        "link": item["source_url"], "match_score": 0, "why_recommended": [],
    }
