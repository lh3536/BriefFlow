"""Assemble a JSON-compatible brief; deterministic summary is the baseline.

Output contract (plus additive summary_mode provenance): preference, total_items, recommended_items,
summary. Items are deep-copied without re-ranking or truncation. When an LLM
is configured, summary may be LLM-written after validation; any failure
falls back to the deterministic factual summary. See docs/AGENT_LLM.md.
"""
from copy import deepcopy
from math import isfinite

from backend.output_agent.llm import summarize_with_llm

HIGH_MATCH_THRESHOLD = 80


def _is_high_match(item: dict) -> bool:
    """Display label for an existing finite score of 80-100; not a new rule."""
    score = item.get("match_score")
    return (
        type(score) in (int, float)
        and 0 <= score <= 100
        and isfinite(score)
        and score >= HIGH_MATCH_THRESHOLD
    )


def _deterministic_summary(total: int, high_matches: int) -> str:
    if total:
        return f"根据你的需求，本次找到 {total} 条匹配信息，其中 {high_matches} 条高度匹配。"
    return "根据你的需求，本次未找到匹配信息，可尝试补充或调整需求。"


def build_brief(preference: dict[str, list[str]], ranked_items: list[dict]) -> dict:
    """Copy input data unchanged and summarize; optional LLM summary on top.

    High match is a display label for an existing finite score of 80-100,
    not a probability or a new ranking rule. Inputs must be JSON-compatible.
    """
    items = deepcopy(ranked_items)
    total = len(items)
    high_matches = sum(1 for item in items if _is_high_match(item))
    summary = _deterministic_summary(total, high_matches)
    llm_summary = summarize_with_llm(preference, items)
    if llm_summary:
        summary = llm_summary
    return {
        "preference": deepcopy(preference),
        "total_items": total,
        "recommended_items": items,
        "summary": summary,
        "summary_mode": "llm" if llm_summary else "deterministic",
    }
