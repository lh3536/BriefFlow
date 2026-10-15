"""Tier-based feature gating (mock for competition demo).

三级付费方案：free / plus / pro。门控点放在「理解用户输入」之后、检索之前：
按 tier 截断偏好维度（按优先级），并在排序后按 tier 限制结果条数。

维度优先级：类型 > 地点 > 专业 > 年级 > 时间偏好 > 关键词。
排除词（exclude_keywords）永远豁免，不被截断——它是纠错/保底，不是增强。
"""

TIERS = {
    "free": {
        "name": "Free",
        "price": 0,
        "dims": 1,          # 只保留最高优先级 1 个维度（类型）
        "limit": 5,         # 最多返回 5 条
        "history": 5,
    },
    "plus": {
        "name": "Plus",
        "price": 19,
        "dims": 4,          # 类型 + 地点 + 专业 + 年级
        "limit": 20,
        "history": 50,
    },
    "pro": {
        "name": "Pro",
        "price": 39,
        "dims": 99,         # 全部维度
        "limit": None,      # 不限条数
        "history": None,    # 不限历史
    },
}

# 维度优先级（截断顺序）
DIM_ORDER = ["categories", "locations", "disciplines", "grades", "time_prefs", "keywords"]

# 豁免字段：永不截断
EXEMPT_FIELDS = {"exclude_keywords"}

# 供前端展示的维度中文名
DIM_LABELS = {
    "categories": "类型",
    "locations": "地点",
    "disciplines": "专业",
    "grades": "年级",
    "time_prefs": "时间偏好",
    "keywords": "关键词",
}


def resolve_tier(tier) -> str:
    """规范化 tier，未知值回退到 free。"""
    return tier if tier in TIERS else "free"


def apply_tier_gate(preference: dict, tier: str) -> tuple[dict, list[str]]:
    """按 tier 截断偏好维度，返回 (截断后的 preference, 被截断的维度字段名)。

    原地修改 preference；排除词豁免。规则：
    - 按 DIM_ORDER 优先级顺序，仅保留前 dims 个「非空」维度，其余置空。
    - exclude_keywords 等 EXEMPT_FIELDS 永远保留。
    """
    tier = resolve_tier(tier)
    max_dims = TIERS[tier]["dims"]
    dropped: list[str] = []
    kept = 0
    for field in DIM_ORDER:
        values = preference.get(field)
        if not values:
            continue
        if kept < max_dims:
            kept += 1
        else:
            preference[field] = []
            dropped.append(field)
    return preference, dropped


def result_limit(tier: str) -> int | None:
    """该 tier 的结果条数上限；None 表示不限。"""
    return TIERS[resolve_tier(tier)]["limit"]
