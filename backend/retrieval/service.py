"""Read existing mock records without changing the source dataset.

TODO: 后续由 Retrieval Owner 接入 Database / Web Crawler。
"""
import json
from pathlib import Path

MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mock" / "mock_db.json"


def get_items(preference: dict[str, list[str]]) -> list[dict]:
    """Return fresh mock records; preference filtering belongs to ranking in V0.1.

    Each item has job_id, title, company, location, category, deadline, link,
    match_score and why_recommended. File/JSON errors propagate to the caller.
    """
    with MOCK_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)
