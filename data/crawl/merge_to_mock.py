"""把筛选后的夏令营合并到 mock_db.json。"""
import json
from pathlib import Path

MOCK = Path(__file__).resolve().parents[1] / "mock" / "mock_db.json"
FILTERED = Path(__file__).parent / "summer_camp_filtered.json"

mock = json.loads(MOCK.read_text(encoding="utf-8"))
filtered = json.loads(FILTERED.read_text(encoding="utf-8"))

existing_titles = {x["title"] for x in mock}
new_items = [x for x in filtered if x["title"] not in existing_titles]

merged = mock + new_items
MOCK.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"原 {len(mock)} 条 + 新增 {len(new_items)} 条 = {len(merged)} 条")