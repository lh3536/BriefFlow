"""V0.1 policy weights, not statistically calibrated predictions."""

# 匹配分七维度，权重总和 100
WEIGHTS = {
    "location": 25,
    "disciplines": 15,
    "category": 20,
    "grades": 10,
    "time_pref": 10,
    "keyword": 10,
    "timeliness": 10,
    "match_priority": 0.8,
    "deadline": 10,
    "freshness": 10,
}

# Inclusive day boundaries: encourage action near closing, then recent discovery.
DEADLINE_BANDS = ((3, 1.0), (7, 0.6), (14, 0.3))
FRESHNESS_BANDS = ((7, 1.0), (30, 0.5))
EXCLUDE_EXPANSIONS = {"销售": ("销售", "保险代理", "电话营销", "地推", "客服销售")}
PRIORITY_MULTIPLIER_RANGE = (0.0, 3.0)

# 特殊地点值：不参与硬过滤，只参与软打分
SPECIAL_LOCATIONS = {"未注明", "全国", "线上", "多个城市"}
