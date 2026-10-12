"""Optional LLM-written summary for the brief (AO scope).

The deterministic factual summary stays the fallback and is always computed.
An LLM summary is used only when it passes validation (short plain text);
scores, ordering and item data are never sent back modified, and the LLM is
never asked to rank. Any failure returns None.
"""
from __future__ import annotations

import json

from backend.llm import chat_completion, llm_available

_MAX_SUMMARY_LENGTH = 200
_TOP_ITEMS_SHOWN = 5

_SYSTEM_PROMPT = """你是 BriefFlow 的简报撰写助手。根据给定的用户偏好和推荐结果，写一段不超过 80 字的中文摘要。

要求：
- 只输出摘要正文，不要 JSON、不要列表、不要引号。
- 先说总体结论（找到几条、几条高度匹配），再点出最值得关注的 1-2 条（标题或地点）。
- 只能使用给定数据，禁止编造条目不存在的信息，禁止修改分数含义。
- 如果总数为 0，温和地说明没有找到，并建议补充或调整需求。"""


def _is_valid_summary(text: str) -> bool:
    """Plain short text only; reject JSON blobs, markdown noise and empties."""
    if not text or len(text) > _MAX_SUMMARY_LENGTH:
        return False
    if any(marker in text for marker in ("{", "}", "```", "**")):
        return False
    return True


def summarize_with_llm(
    preference: dict[str, list[str]],
    ranked_items: list[dict],
    *,
    retries: int = 1,
) -> str | None:
    """Best-effort LLM summary; None when disabled or all attempts fail."""
    if not llm_available():
        return None
    total = len(ranked_items)
    high = sum(
        1 for item in ranked_items
        if isinstance(item.get("match_score"), (int, float))
        and not isinstance(item.get("match_score"), bool)
        and 80 <= item["match_score"] <= 100
    )
    top_items = [
        {
            "title": item.get("title"),
            "location": item.get("location"),
            "match_score": item.get("match_score"),
            "deadline": item.get("deadline"),
        }
        for item in ranked_items[:_TOP_ITEMS_SHOWN]
    ]
    user_content = json.dumps(
        {"preference": preference, "total": total, "high_match": high, "top_items": top_items},
        ensure_ascii=False,
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    for attempt in range(retries + 1):
        try:
            content = chat_completion(messages).strip()
        except Exception:
            if attempt >= retries:
                return None
            continue
        if _is_valid_summary(content):
            return content
        if attempt >= retries:
            return None
    return None
