"""Small SQLite source-record store; ranking fields are intentionally absent."""
from contextlib import closing
import json
import logging
from pathlib import Path
import sqlite3

from backend.retrieval.schema import FIELDS, content_key, normalize_item, validate_item

LOGGER = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path(__file__).resolve().parent / ".cache" / "items.sqlite3"
LIST_FIELDS = ("tags", "requirements", "disciplines", "grades")
SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY, title TEXT NOT NULL, organization TEXT NOT NULL,
    location TEXT NOT NULL, category TEXT NOT NULL, module TEXT NOT NULL,
    summary TEXT NOT NULL,
    source TEXT NOT NULL, source_url TEXT NOT NULL UNIQUE,
    published_at TEXT NOT NULL, deadline TEXT NOT NULL,
    tags TEXT NOT NULL, requirements TEXT NOT NULL,
    disciplines TEXT NOT NULL, grades TEXT NOT NULL, time_pref TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    content_key TEXT NOT NULL UNIQUE
)
"""

LEGACY_COLUMNS = {
    "module": "TEXT NOT NULL DEFAULT ''",
    "disciplines": "TEXT NOT NULL DEFAULT '[]'",
    "grades": "TEXT NOT NULL DEFAULT '[]'",
    "time_pref": "TEXT NOT NULL DEFAULT ''",
}


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Create the cache table and add compatible columns to legacy caches."""
    connection.execute(SCHEMA)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(items)")}
    for name, definition in LEGACY_COLUMNS.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE items ADD COLUMN {name} {definition}")


def save_items(items: list[dict], path: Path = DEFAULT_DB_PATH) -> int:
    """Validate and upsert by URL; skip invalid records and content/ID collisions."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    saved = 0
    with closing(sqlite3.connect(path)) as connection, connection:
        _ensure_schema(connection)
        fields = (*FIELDS, "content_key")
        updates = ", ".join(f"{key}=excluded.{key}" for key in fields if key not in ("item_id", "source_url"))
        sql = f"INSERT INTO items ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)}) ON CONFLICT(source_url) DO UPDATE SET {updates}"
        for index, raw in enumerate(items):
            try:
                item = normalize_item(raw)
                errors = validate_item(item)
                if errors:
                    raise ValueError("; ".join(errors))
                values = [json.dumps(item[key], ensure_ascii=False) if key in LIST_FIELDS else item[key] for key in FIELDS]
                connection.execute(sql, [*values, content_key(item)])
                saved += 1
            except (ValueError, TypeError, sqlite3.IntegrityError) as exc:
                LOGGER.warning("database_record_skipped index=%s reason=%s", index, str(exc))
    return saved


def load_items(path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Read records; leave malformed list fields for pipeline validation/counting."""
    path = Path(path)
    if not path.exists():
        return []
    result = []
    with closing(sqlite3.connect(path)) as connection, connection:
        _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        for row in connection.execute(f"SELECT {','.join(FIELDS)} FROM items ORDER BY item_id"):
            item = dict(row)
            for key in LIST_FIELDS:
                try:
                    item[key] = json.loads(item[key])
                except (ValueError, TypeError):
                    LOGGER.warning("database_invalid_json field=%s", key)
            result.append(item)
    return result
