"""Offline rule-based fallback; no LLM, API key or network required.

This intentionally bounded parser is not general language understanding.
Any future optional LLM must validate its JSON and fall back to these rules.
"""
import re
import unicodedata


_EXCLUSION = re.compile(
    r"(?:不想要|不想做|不想找|不要|排除|不考虑|不接受|避免)"
    r"(.*?)"
    r"(?=[,，。.;；!！?？\n\r]|但|不过|想找|希望|只要|要找|需要|$)"
)


def parse_user_request(text: str) -> dict[str, list[str]]:
    """Return categories, locations, keywords and exclude_keywords lists.

    Supports the four mock categories/cities and a fixed exclusion vocabulary.
    Unknown terms are ignored; blank input returns empty lists.
    Non-string input raises ValueError. See docs/input_output_changes.md.
    """
    if not isinstance(text, str):
        raise ValueError("User request must be a string")
    text = unicodedata.normalize("NFKC", text).strip()

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
