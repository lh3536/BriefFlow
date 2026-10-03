"""Small keyword parser for the V0.1 demo, not general language understanding.

TODO: 后续由 AI Agent Owner 替换为真正 LLM Agent。
"""
import re


def parse_user_request(text: str) -> dict[str, list[str]]:
    """Return categories, locations, keywords and exclude_keywords lists.

    Supports the four mock categories/cities and a fixed exclusion vocabulary.
    Unknown terms are ignored; blank input raises ValueError.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("User request must be a nonempty string")

    exclusions = re.findall(r"(?:不要|排除|不考虑)([^，。；！？\n]+)", text)
    positive_text = re.sub(r"(?:不要|排除|不考虑)[^，。；！？\n]+", "", text)
    categories = [
        category for category, aliases in (
            ("金融实习", ("金融实习", "实习")),
            ("经管比赛", ("经管比赛", "比赛")),
            ("夏令营", ("夏令营",)),
            ("科研机会", ("科研", "研究助理")),
        ) if any(alias in positive_text for alias in aliases)
    ]
    locations = [
        city for city in ("广州", "深圳", "香港", "澳门")
        if city in positive_text or "粤港澳" in positive_text
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
