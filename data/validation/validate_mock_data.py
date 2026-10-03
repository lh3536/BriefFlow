"""Validate synthetic BriefFlow opportunities using only the standard library."""
from datetime import date
import json
from pathlib import Path
import re

REQUIRED = {"job_id", "title", "company", "location", "category", "deadline", "link", "match_score", "why_recommended"}
FORBIDDEN = ("销售", "销售代表", "客户经理销售方向", "电话营销", "地推", "客服", "保险代理")


def validate(path: Path) -> list[str]:
    """Parse with json.load and check schema, domain rules, and score sums."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    errors: list[str] = []
    if not isinstance(data, list) or len(data) != 15:
        return ["Root must be a list with exactly 15 records"]
    ids = []
    cities = set()
    for i, row in enumerate(data, 1):
        label = f"Record {i}"
        if not isinstance(row, dict) or set(row) != REQUIRED:
            errors.append(f"{label}: exact required fields missing or extra fields")
            continue
        ids.append(row["job_id"])
        if row["job_id"] != f"job_{i:03d}":
            errors.append(f"{label}: unexpected job_id")
        if row["location"] not in ("广州", "深圳", "香港", "澳门"):
            errors.append(f"{label}: invalid location")
        else:
            cities.add(row["location"])
        if row["category"] not in ("金融实习", "经管比赛", "夏令营", "科研机会"):
            errors.append(f"{label}: invalid category")
        try:
            assert isinstance(row["deadline"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["deadline"])
            assert date(2026, 10, 1) <= date.fromisoformat(row["deadline"]) <= date(2026, 12, 31)
        except (AssertionError, ValueError, TypeError):
            errors.append(f"{label}: invalid deadline")
        if type(row["match_score"]) is not int or not 0 <= row["match_score"] <= 100:
            errors.append(f"{label}: score must be integer 0–100")
        reasons = row["why_recommended"]
        if not isinstance(reasons, list) or not reasons or not all(isinstance(r, str) and re.fullmatch(r".+\+\d+", r) for r in reasons):
            errors.append(f"{label}: reasons must be nonempty list of scoring explanations")
        elif sum(int(r.rsplit("+", 1)[1]) for r in reasons) != row["match_score"]:
            errors.append(f"{label}: reason points do not sum to score")
        if row["link"] != f"https://example.com/job_{i:03d}":
            errors.append(f"{label}: invalid example.com link")
        if any(word in json.dumps(row, ensure_ascii=False) for word in FORBIDDEN):
            errors.append(f"{label}: forbidden keyword")
        for field in REQUIRED - {"match_score", "why_recommended"}:
            if not isinstance(row[field], str) or not row[field].strip():
                errors.append(f"{label}: {field} must be nonempty string")
    if len({str(x) for x in ids}) != 15:
        errors.append("IDs must be unique")
    if cities != {"广州", "深圳", "香港", "澳门"}:
        errors.append("All four cities must be represented")
    return errors


if __name__ == "__main__":
    try:
        failures = validate(Path(__file__).resolve().parents[1] / "mock" / "mock_db.json")
    except (OSError, ValueError) as exc:
        failures = [str(exc)]
    print("FAIL: " + "\n".join(failures) if failures else "PASS: json.load; 15 records; unique job_001–job_015; exact schema; 4 cities; categories; dates; integer scores; explanation lists and score sums; forbidden keywords absent; example.com links")
    raise SystemExit(bool(failures))
