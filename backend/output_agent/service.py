"""Backward-compatible brief, with grounded summary and optional highlights."""
from copy import deepcopy

from backend.output_agent.llm import summarize_with_llm
from backend.output_agent.presentation import (
    HIGH_MATCH_THRESHOLD, describe_items, is_high_match, sentence_options,
)

_is_high_match = is_high_match


def build_brief(preference: dict[str, list[str]], ranked_items: list[dict]) -> dict:
    """Deep-copy the full ranking unchanged; add factual presentation metadata."""
    items = deepcopy(ranked_items)
    stats = describe_items(items)
    options = sentence_options(items, stats)
    deterministic = "".join(slot[0] for slot in options)
    llm_summary = summarize_with_llm(preference, items, options=options)
    highlights = [f"{stats['high_match']} 条高匹配机会",
                  f"{stats['urgent_deadline']} 条 7 天内截止"]
    if stats["expired"]:
        highlights.append(f"{stats['expired']} 条已截止")
    return {
        "preference": deepcopy(preference),
        "total_items": len(items),
        "recommended_items": items,
        "summary": llm_summary or deterministic,
        "summary_mode": "llm" if llm_summary else "deterministic",
        "highlights": highlights,
        "result_stats": stats,
    }
