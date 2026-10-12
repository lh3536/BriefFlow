"""Factual display metadata only: never filter, score or reorder opportunities."""
from datetime import date, datetime, timedelta, timezone
from math import isfinite
import os

HIGH_MATCH_THRESHOLD = 80
LOCAL_TIMEZONE = timezone(timedelta(hours=8))


def is_high_match(item: dict) -> bool:
    score = item.get("match_score")
    return type(score) in (int, float) and isfinite(score) and 80 <= score <= 100


def deadline_days(item: dict, today: date) -> int | None:
    value = item.get("deadline")
    try:
        return (date.fromisoformat(value) - today).days if isinstance(value, str) else None
    except ValueError:
        return None


def describe_items(items: list[dict], *, as_of: date | None = None,
                   requested_mode: str | None = None) -> dict:
    today = as_of or datetime.now(LOCAL_TIMEZONE).date()
    mode = (requested_mode if requested_mode is not None else
            os.environ.get("BRIEFFLOW_RETRIEVAL_MODE", "mock")).strip().lower()
    days = [deadline_days(item, today) for item in items]
    mock_count = sum("mock" in str(item.get("source", "")).casefold() for item in items)
    # Empty results contain no source evidence. Never infer a successful live fetch.
    if mock_count:
        source = "Mock Data" if mock_count == len(items) else "Mixed / 含 Mock Data"
    elif mode == "mock" or mode not in ("web", "database"):
        source = "Mock Data" if not items else "Unknown / 来源待核实"
    else:
        source = {"web": "Web", "database": "Database"}[mode]
        if not items:
            source += " / 无结果，来源未确认"
    return {
        "total": len(items),
        "high_match": sum(is_high_match(item) for item in items),
        "urgent_deadline": sum(day is not None and 0 <= day <= 7 for day in days),
        "expired": sum(day is not None and day < 0 for day in days),
        "as_of": today.isoformat(),
        "data_source_mode": source,
        "mock_count": mock_count,
        "retrieval_fallback": bool(mock_count and mode in ("web", "database")),
    }


def sentence_options(items: list[dict], stats: dict) -> list[list[str]]:
    """Approved factual wording; every LLM sentence must come from one slot."""
    total, high = stats["total"], stats["high_match"]
    if not total:
        return [["根据你的需求，本次未找到匹配信息。"],
                ["可以尝试调整地点或机会类型，再查看结果。"]]
    slots = [[
        f"本次共筛选出 {total} 条与你需求相关的机会，其中 {high} 条高度匹配。",
        f"这次为你整理了 {total} 条相关机会，其中 {high} 条高度匹配。",
    ]]
    today = date.fromisoformat(stats["as_of"])
    titles = [item["title"].strip() for item in items
              if isinstance(item.get("title"), str) and item["title"].strip()
              and (deadline_days(item, today) is None or deadline_days(item, today) >= 0)][:2]
    if titles:
        focus = "、".join(f"《{title}》" for title in titles)
        slots.append([f"按当前推荐顺序，建议先查看{focus}。",
                      f"可以先从{focus}看起，再核实来源中的申请要求。"])
    else:
        slots.append(["建议先核实各条目的截止日期和申请要求，再决定是否申请。"])
    urgent, expired = stats["urgent_deadline"], stats["expired"]
    if urgent:
        slots.append([f"另有 {urgent} 条机会将在 7 天内截止（含今天），建议及时查看。"])
    elif expired:
        slots.append([f"其中 {expired} 条已过标注截止日期，请以来源最新信息为准。"])
    if stats["mock_count"]:
        slots.append(["其中的 Mock 条目仅供演示，不是真实招聘或报名信息。"])
    return slots
