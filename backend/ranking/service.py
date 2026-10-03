"""Explainable offline match scoring and time-aware delivery priority."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import logging
from math import isfinite

from backend.ranking.config import (
    DEADLINE_BANDS, EXCLUDE_EXPANSIONS, FRESHNESS_BANDS,
    PRIORITY_MULTIPLIER_RANGE, WEIGHTS,
)

LOGGER = logging.getLogger(__name__)
LOCAL_TIMEZONE = timezone(timedelta(hours=8))


def _terms(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(term.strip() for term in value if isinstance(term, str) and term.strip()))


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _date(value) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _match_weights(preference: dict) -> dict[str, float]:
    """Optional priority_weights multiplies dimensions, normalized back to 100."""
    custom = preference.get("priority_weights", {})
    if not isinstance(custom, dict):
        custom = {}
    adjusted = {}
    low, high = PRIORITY_MULTIPLIER_RANGE
    for key in ("location", "category", "keyword"):
        multiplier = custom.get(key, 1)
        if type(multiplier) not in (int, float) or not low <= multiplier <= high or not isfinite(multiplier):
            multiplier = 1
        adjusted[key] = WEIGHTS[key] * multiplier
    total = sum(adjusted.values())
    if not total:
        return {key: WEIGHTS[key] for key in adjusted}
    # Largest-remainder allocation: nonnegative hundredths sum to exactly 100.
    scaled = {key: 10000 * value / total for key, value in adjusted.items()}
    cents = {key: int(value) for key, value in scaled.items()}
    order = sorted(cents, key=lambda key: -(scaled[key] - cents[key]))
    for key in order[:10000 - sum(cents.values())]:
        cents[key] += 1
    return {key: value / 100 for key, value in cents.items()}


def _bonus(days: int | None, bands: tuple, weight: float) -> float:
    if days is not None and days >= 0:
        for limit, fraction in bands:
            if days <= limit:
                return round(weight * fraction, 2)
    return 0


def rank_items(preference: dict, items: list[dict], *, as_of: date | None = None,
               user_feedback_weights: dict | None = None) -> list[dict]:
    """Keep the two-argument Router API; optional controls never require an LLM.

    why_recommended sums to match_score; priority_reasons sums to priority_score.
    TODO: define an approved feedback contract before applying learning/penalties.
    user_feedback_weights is reserved and currently has no scoring effect.
    """
    today = as_of if as_of is not None else datetime.now(LOCAL_TIMEZONE).date()
    if type(today) is not date:
        raise ValueError("as_of must be a date")
    if user_feedback_weights:
        LOGGER.info("user_feedback_weights reserved; no feedback adjustment applied")
    locations = _terms(preference.get("locations"))
    categories = _terms(preference.get("categories"))
    keywords = _terms(preference.get("keywords"))
    exclusions = [alias.casefold() for term in _terms(preference.get("exclude_keywords"))
                  for alias in EXCLUDE_EXPANSIONS.get(term, (term,))]
    if not any((locations, categories, keywords)):
        return []
    weights = _match_weights(preference)
    ranked = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # Exclude matching includes descriptions/requirements; old explanations never count.
        match_text = " ".join(_text(item.get(key)) for key in ("title", "company", "organization", "category")).casefold()
        exclude_text = " ".join([match_text, _text(item.get("summary")),
                                 *_terms(item.get("tags")), *_terms(item.get("requirements"))]).casefold()
        if any(term in exclude_text for term in exclusions):
            continue
        if locations and item.get("location") not in locations:
            continue
        if categories and item.get("category") not in categories:
            continue
        matched_keywords = [word for word in keywords if word.casefold() in match_text]
        contributions = {"location": weights["location"] if locations else 0,
                         "category": weights["category"] if categories else 0,
                         "keyword": weights["keyword"] if matched_keywords else 0}
        match_score = round(sum(contributions.values()), 2)
        if match_score <= 0:
            continue
        labels = {"location": f"地点匹配（{item.get('location', '')}）",
                  "category": f"类别匹配（{item.get('category', '')}）",
                  "keyword": f"关键词匹配（{'、'.join(matched_keywords)}）"}
        reasons = [f"{labels[key]}+{value:g}" for key, value in contributions.items() if value]
        deadline, published = _date(item.get("deadline")), _date(item.get("published_at"))
        expired = deadline is not None and deadline < today
        deadline_bonus = _bonus((deadline - today).days if deadline else None, DEADLINE_BANDS, WEIGHTS["deadline"])
        freshness_bonus = _bonus((today - published).days if published else None, FRESHNESS_BANDS, WEIGHTS["freshness"])
        base = round(match_score * WEIGHTS["match_priority"], 2)
        priority_parts = {"match": base, "deadline": deadline_bonus, "freshness": freshness_bonus}
        priority_reasons = [f"匹配分 × {WEIGHTS['match_priority']:g}+{base:g}"]
        if deadline_bonus:
            priority_reasons.append(f"距截止 {(deadline - today).days} 天+{deadline_bonus:g}")
        if freshness_bonus:
            priority_reasons.append(f"发布距今 {(today - published).days} 天+{freshness_bonus:g}")
        raw_priority = round(sum(priority_parts.values()), 2)
        if expired:
            priority_parts["expired"] = -raw_priority
            priority_reasons.append(f"已截止，停止优先推送{-raw_priority:+g}")
        priority = max(0, min(100, round(sum(priority_parts.values()), 2)))
        ranked.append({**deepcopy(item), "match_score": match_score, "priority_score": priority,
                       "why_recommended": reasons, "priority_reasons": priority_reasons,
                       "score_breakdown": {"match": contributions, "priority": priority_parts},
                       "deadline_expired": expired})

    def sort_key(item):
        deadline, published = _date(item.get("deadline")), _date(item.get("published_at"))
        # Future publication dates earn no freshness and get no publication tie advantage.
        published_order = published.toordinal() if published and published <= today else 0
        return (-item["priority_score"], -item["match_score"], deadline or date.max,
                -published_order, _text(item.get("job_id") or item.get("item_id")),
                json.dumps(item, ensure_ascii=False, sort_keys=True, default=str))

    ranked.sort(key=sort_key)
    for position, item in enumerate(ranked, 1):
        item["final_rank"] = position
    return ranked
