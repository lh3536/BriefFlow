"""Assemble the shared JSON-compatible output contract.

TODO: 后续由 AI Agent Owner 增加摘要、解释、个性化输出。
"""


def build_brief(preference: dict[str, list[str]], ranked_items: list[dict]) -> dict:
    """Wrap recommendations without changing their order or scores."""
    return {
        "preference": preference,
        "total_items": len(ranked_items),
        "recommended_items": ranked_items,
    }
