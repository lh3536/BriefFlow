"""Assemble a JSON-compatible brief with a deterministic factual summary."""
from copy import deepcopy
from math import isfinite

HIGH_MATCH_THRESHOLD = 80


def build_brief(preference: dict[str, list[str]], ranked_items: list[dict]) -> dict:
    """Copy input data unchanged and summarize counts, without LLM calls.

    High match is a display label for an existing finite score of 80–100,
    not a probability or a new ranking rule. Inputs must be JSON-compatible.
    """
    items = deepcopy(ranked_items)
    total = len(items)
    high_matches = sum(
        1 for item in items
        if type(score := item.get("match_score")) in (int, float)
        and 0 <= score <= 100 and isfinite(score)
        and score >= HIGH_MATCH_THRESHOLD
    )
    summary = (
        f"根据你的需求，本次找到 {total} 条匹配信息，其中 {high_matches} 条高度匹配。"
        if total else "根据你的需求，本次未找到匹配信息，可尝试补充或调整需求。"
    )
    return {
        "preference": deepcopy(preference),
        "total_items": total,
        "recommended_items": items,
        "summary": summary,
    }
