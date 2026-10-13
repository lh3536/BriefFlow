"""V0.1 policy weights, not statistically calibrated predictions."""

# RC2: location + category alone are 70, below the existing high-match threshold.
# Keyword points scale with requested-term coverage. Timing only affects priority.
WEIGHTS = {"location": 35, "category": 35, "keyword": 30,
           "match_priority": 0.8, "deadline": 10, "freshness": 10}
# Inclusive day boundaries: encourage action near closing, then recent discovery.
DEADLINE_BANDS = ((3, 1.0), (7, 0.6), (14, 0.3))
FRESHNESS_BANDS = ((7, 1.0), (30, 0.5))
EXCLUDE_EXPANSIONS = {"销售": ("销售", "保险代理", "电话营销", "地推", "客服销售")}
PRIORITY_MULTIPLIER_RANGE = (0.0, 3.0)
