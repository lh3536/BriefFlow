"""Optional LLM enhancement for preference parsing (AO scope).

The deterministic rule parser stays the baseline. A validated LLM result is
merged (union) with the rule result, so the LLM can extend coverage to
phrasing the rules miss but can never remove a rule-recognized condition or
break the Preference contract. Any failure returns None and the caller uses
rules alone.
"""
from __future__ import annotations

import json
import re

from backend.llm import chat_completion, llm_available

# Downstream (Kami's retrieval, Flin's ranking) only understands these values;
# anything else the LLM invents is dropped instead of breaking hard filters.
_ALLOWED_CATEGORIES = ("金融实习", "经管比赛", "夏令营", "科研机会")
_ALLOWED_LOCATIONS = ("广州", "深圳", "香港", "澳门")
_MAX_ITEMS = 10
_MAX_WORD_LENGTH = 20

_SYSTEM_PROMPT = """你是 BriefFlow 的需求理解助手。把用户的需求原文解析为 JSON，只输出 JSON，不要输出任何其他文字。

输出格式（四个字段都是字符串列表，没有识别到就给空列表，禁止编造）：
{"categories": [...], "locations": [...], "keywords": [...], "exclude_keywords": [...]}

约束：
- categories 只能从 ["金融实习", "经管比赛", "夏令营", "科研机会"] 中选择。
- locations 只能从 ["广州", "深圳", "香港", "澳门"] 中选择；"广深"指广州和深圳，"港澳"指香港和澳门，"粤港澳"指四城。
- keywords 是用户感兴趣的方向词（如 金融、量化、投行、研究、科技，或原文中其他明确兴趣词）。
- exclude_keywords 是用户明确表示不想要的词（"不要/排除/不考虑/避免"等后面的内容）。
- 用户没有提到的维度一律给空列表。"""

_JSON_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)


def _extract_json(content: str) -> dict:
    """Pull the first JSON object out of an LLM response; raises on failure."""
    match = _JSON_OBJECT.search(content.strip())
    if not match:
        raise ValueError("LLM response contains no JSON object")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM JSON is not an object")
    return data


def _string_list(value: object) -> list[str]:
    """Keep non-empty short strings only, deduplicated, order preserved."""
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and len(cleaned) <= _MAX_WORD_LENGTH and cleaned not in result:
                result.append(cleaned)
    return result[:_MAX_ITEMS]


def validate_preference(data: dict) -> dict[str, list[str]]:
    """Coerce an LLM JSON object into the Preference contract.

    Categories/locations outside the allowed vocabularies are dropped so the
    downstream hard filters never see invented values.
    """
    return {
        "categories": [word for word in _string_list(data.get("categories")) if word in _ALLOWED_CATEGORIES],
        "locations": [word for word in _string_list(data.get("locations")) if word in _ALLOWED_LOCATIONS],
        "keywords": _string_list(data.get("keywords")),
        "exclude_keywords": _string_list(data.get("exclude_keywords")),
    }


def parse_with_llm(text: str, *, retries: int = 1) -> dict[str, list[str]] | None:
    """Best-effort LLM parse; None when disabled or after all retries fail."""
    if not llm_available():
        return None
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    for attempt in range(retries + 1):
        try:
            return validate_preference(_extract_json(chat_completion(messages)))
        except Exception:
            if attempt >= retries:
                return None
    return None


def merge_preferences(
    rule_result: dict[str, list[str]],
    llm_result: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    """Union merge: rules are the floor, LLM can only add recognized items."""
    if not llm_result:
        return rule_result
    return {
        field: list(dict.fromkeys([*rule_result.get(field, []), *llm_result.get(field, [])]))
        for field in ("categories", "locations", "keywords", "exclude_keywords")
    }
