"""Compose module interfaces; domain logic stays with each owner."""
from backend.input_agent.service import parse_user_request
from backend.output_agent.service import build_brief
from backend.ranking.service import rank_items
from backend.retrieval.service import get_items
from backend.output_agent.presentation import describe_items
import os


def run_brief_flow(user_text: str) -> dict:
    """Run user input through parsing, retrieval, ranking and output assembly."""
    trace = {}
    preference = parse_user_request(user_text, trace=trace)
    items = get_items(preference)
    # Capture source evidence BEFORE ranking can remove all the live results.
    source_stats = describe_items(items)
    ranked_items = rank_items(preference, items)
    result = build_brief(preference, ranked_items)
    result.update(trace)
    result['retrieval'] = {
        'requested_mode': os.environ.get('BRIEFFLOW_RETRIEVAL_MODE', 'mock').strip().lower(),
        'data_source_mode': source_stats['data_source_mode'],
        'retrieved_count': len(items),
        'mock_count': source_stats['mock_count'],
        'fallback': source_stats['retrieval_fallback'],
    }
    return result

