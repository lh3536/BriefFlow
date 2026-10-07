"""Input Agent: deterministic rules are the baseline, LLM is optional.

The public contract is unchanged: parse_user_request(text) -> dict with four
string-list fields. With no API key, no network or any LLM failure, behavior
is exactly the rule-based parser. See docs/input_output_changes.md and
docs/AGENT_LLM.md.
"""
import re
import unicodedata

from backend.input_agent.llm import merge_preferences, parse_with_llm


_EXCLUSION = re.compile(
    r"(?:不想要|不想做|不想找|不要|排除|不考虑|不接受|避免)"
    r"(.*?)"
    r"(?=[,，。.;；!！?？\n\r]|但|不过|想找|希望|只要|要找|需要|$)"
)


def parse_user_request(text: str) -> dict[str, list[str]]:
    """Return categories, locations, keywords and exclude_keywords lists.

    Rule results are always computed; when an LLM is configured its validated
    result is merged in (union), otherwise the rule result is returned as-is.
    Blank input returns four empty lists without calling the LLM.
    Non-string input raises ValueError. See docs/input_output_changes.md.
    """
    if not isinstance(text, str):
        raise ValueError("User request must be a string")
    normalized = unicodedata.normalize("NFKC", text).strip()

    rule_result = _rule_parse(normalized)
    if not normalized:
        return rule_result
    return merge_preferences(rule_result, parse_with_llm(normalized))


def _rule_parse(text: str) -> dict[str, list[str]]:
    """The original V0.1 keyword parser; intentionally bounded.

    This is not general language understanding. It supports the four mock
    categories/cities and a fixed exclusion vocabulary; unknown terms are
    ignored. Any LLM enhancement must fall back to these rules.
    """
    exclusions = _EXCLUSION.findall(text)
    positive_text = _EXCLUSION.sub(" ", text)
    categories = [
        category for category, aliases in (
            ("金融实习", ("金融实习", "实习")),
            ("经管比赛", ("经管比赛", "比赛")),
            ("夏令营", ("夏令营",)),
            ("科研机会", ("科研", "研究助理")),
        ) if any(alias in positive_text for alias in aliases)
    ]
    locations = [
        city for city, alias in (("广州", "广深"), ("深圳", "广深"), ("香港", "港澳"), ("澳门", "港澳"))
        if city in positive_text or alias in positive_text or "粤港澳" in positive_text
    ]
    keywords = [word for word in ("金融", "量化", "投行", "研究", "科技") if word in positive_text]
    exclude_keywords = [
        word for word in ("销售", "客服", "保险", "地推", "电话营销")
        if any(word in clause for clause in exclusions)
    ]
    return {
        "categories": categories,
        "locations": locations,
        "keywords": keywords,
        "exclude_keywords": exclude_keywords,
    }
