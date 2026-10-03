"""Minimal filtering and scoring rules for the V0.1 handoff.

TODO: 后续由 Ranking Agent Owner 优化 Priority / Personalization。
"""


def rank_items(preference: dict[str, list[str]], items: list[dict]) -> list[dict]:
    """Filter requested locations/categories and excluded terms, then score.

    Location +40, category +40, any keyword +20 (maximum 100).
    Search title/company/category only; original mock explanations are not input.
    Ties use job_id ascending. Returns new records, leaving input items untouched.
    No recognized positive preference means no recommendations.
    """
    locations = preference.get("locations", [])
    categories = preference.get("categories", [])
    keywords = preference.get("keywords", [])
    exclusions = preference.get("exclude_keywords", [])
    if not any((locations, categories, keywords)):
        return []

    ranked = []
    for item in items:
        searchable = " ".join(item[field] for field in ("title", "company", "category")).casefold()
        if any(word.casefold() in searchable for word in exclusions):
            continue
        if locations and item["location"] not in locations:
            continue
        if categories and item["category"] not in categories:
            continue

        reasons = []
        score = 0
        if locations:
            score += 40
            reasons.append(f"地点匹配（{item['location']}）+40")
        if categories:
            score += 40
            reasons.append(f"类别匹配（{item['category']}）+40")
        matched_keywords = [word for word in keywords if word.casefold() in searchable]
        if matched_keywords:
            score += 20
            reasons.append(f"关键词匹配（{'、'.join(matched_keywords)}）+20")
        if score:
            ranked.append({**item, "match_score": score, "why_recommended": reasons})
    return sorted(ranked, key=lambda item: (-item["match_score"], item["job_id"]))
