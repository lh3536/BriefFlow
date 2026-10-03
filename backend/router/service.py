"""Compose module interfaces; domain logic stays with each owner."""
from backend.input_agent.service import parse_user_request
from backend.output_agent.service import build_brief
from backend.ranking.service import rank_items
from backend.retrieval.service import get_items


def run_brief_flow(user_text: str) -> dict:
    """Run user input through parsing, retrieval, ranking and output assembly."""
    preference = parse_user_request(user_text)
    items = get_items(preference)
    ranked_items = rank_items(preference, items)
    return build_brief(preference, ranked_items)

