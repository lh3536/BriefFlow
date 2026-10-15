"""Compose module interfaces; domain logic stays with each owner."""
from backend.input_agent.service import parse_user_request
from backend.output_agent.service import build_brief
from backend.ranking.service import rank_items
from backend.retrieval.service import get_items
from backend.output_agent.presentation import describe_items
from backend.tiers import apply_tier_gate, resolve_tier, result_limit
import os


def run_brief_flow(user_text: str, tier: str = "pro") -> dict:
    """Run user input through parsing, tier gating, retrieval, ranking and output assembly.

    tier 在「理解输入」之后立即门控：按优先级截断偏好维度，再在排序后限制条数。
    默认 pro（不截断），向后兼容；前端按会话 tier 显式传入。
    """
    tier = resolve_tier(tier)
    trace = {}
    preference = parse_user_request(user_text, trace=trace)
    preference, dropped_dims = apply_tier_gate(preference, tier)
    items = get_items(preference)
    # Capture source evidence BEFORE ranking can remove all the live results.
    source_stats = describe_items(items)
    ranked_items = rank_items(preference, items)
    limit = result_limit(tier)
    if limit is not None:
        ranked_items = ranked_items[:limit]
    result = build_brief(preference, ranked_items)
    result.update(trace)
    result['tier'] = tier
    result['gated'] = {'dropped_dims': dropped_dims, 'limit': limit}
    result['retrieval'] = {
        'requested_mode': os.environ.get('BRIEFFLOW_RETRIEVAL_MODE', 'mock').strip().lower(),
        'data_source_mode': source_stats['data_source_mode'],
        'retrieved_count': len(items),
        'mock_count': source_stats['mock_count'],
        'fallback': source_stats['retrieval_fallback'],
    }
    return result

