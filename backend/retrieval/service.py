"""Fetch → normalize → validate → deduplicate, with explicit mock fallback."""
import json
from http.client import HTTPException
import logging
import os
from pathlib import Path
import sqlite3
from time import perf_counter
import xml.etree.ElementTree as ET

from backend.retrieval.database import DEFAULT_DB_PATH, load_items, save_items
from backend.retrieval.schema import deduplicate_items, normalize_item, to_pipeline_item, validate_item
from backend.retrieval.sources import WEB_SOURCES, fetch_web

LOGGER = logging.getLogger(__name__)
MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mock" / "mock_db.json"


def _read_mock() -> list[dict]:
    with MOCK_PATH.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError("Mock file must contain an array")
    return [{**item, "source": "BriefFlow Mock"} if isinstance(item, dict) else item for item in raw]


def clean_items(raw_items: list[dict]) -> tuple[list[dict], int, int]:
    """Reject individual malformed records with a reason, retaining valid peers."""
    valid = []
    rejected = 0
    for index, raw in enumerate(raw_items):
        try:
            item = normalize_item(raw)
            errors = validate_item(item)
            if errors:
                raise ValueError("; ".join(errors))
            valid.append(item)
        except (ValueError, TypeError) as exc:
            rejected += 1
            LOGGER.warning("item_rejected index=%s reason=%s", index, str(exc))
    unique, duplicates = deduplicate_items(valid)
    return unique, rejected, duplicates


def _retrieve(mode: str, db_path: Path) -> list[dict]:
    start = perf_counter()
    fetched = rejected = duplicates = 0
    items = []
    status = "ok"
    try:
        raw = {"mock": _read_mock, "database": lambda: load_items(db_path), "web": fetch_web}[mode]()
        fetched = len(raw)
        items, rejected, duplicates = clean_items(raw)
        if mode == "web" and items:
            try:
                save_items(items, db_path)
            except (OSError, sqlite3.Error) as exc:
                LOGGER.warning("database_cache_failed reason=%s", type(exc).__name__)
        return items
    except (OSError, HTTPException, ValueError, TypeError, sqlite3.Error, ET.ParseError):
        status = "error"
        raise
    finally:
        LOGGER.info("retrieval %s", json.dumps({
            "source": {"mock": "BriefFlow Mock", "web": ",".join(WEB_SOURCES), "database": "SQLite"}[mode],
            "mode": mode, "items_fetched": fetched, "items_accepted": len(items),
            "items_rejected": rejected, "duplicates_removed": duplicates,
            "duration": round(perf_counter() - start, 6), "status": status,
        }, ensure_ascii=False))


def get_items(preference: dict[str, list[str]]) -> list[dict]:
    """Keep Router's interface; BRIEFFLOW_RETRIEVAL_MODE selects mock/database/web.

    Default mock requires no network or DB. Web/DB failures or empty results use
    mock, with an explicit warning. Filtering and scoring belong to Ranking.
    """
    mode = os.environ.get("BRIEFFLOW_RETRIEVAL_MODE", "mock").lower().strip()
    db_path = Path(os.environ.get("BRIEFFLOW_DB_PATH", str(DEFAULT_DB_PATH)))
    if mode not in ("mock", "database", "web"):
        LOGGER.warning("unknown_mode mode=%s fallback=mock", mode)
        mode = "mock"
    try:
        items = _retrieve(mode, db_path)
        if items or mode == "mock":
            return [to_pipeline_item(item) for item in items]
        LOGGER.warning("retrieval_empty source=%s fallback=mock", mode)
    except (OSError, HTTPException, ValueError, TypeError, sqlite3.Error, ET.ParseError) as exc:
        LOGGER.warning("retrieval_failed source=%s reason=%s fallback=%s", mode, type(exc).__name__, "mock" if mode != "mock" else "empty")
        if mode == "mock":
            return []
    try:
        return [to_pipeline_item(item) for item in _retrieve("mock", db_path)]
    except (OSError, ValueError, TypeError) as exc:
        LOGGER.warning("mock_fallback_failed reason=%s", type(exc).__name__)
        return []
