# Ranking / Priority V0.1

`rank_items(preference, items)` 仍兼容 Router 的两参数调用，完全离线，不需要 API Key。
只在记录副本中加入评分和排序字段，不修改来源数据、Input/Output Agent 或 Retrieval。

## Match Score 与 Weight Config

权重集中在 `backend/ranking/config.py`。默认沿用原有地点 40、类别 40、任一关键词
20，合计 0–100。地点和类别保持硬筛选；关键词在标题、机构、类别中匹配，不重复叠加。
没有指定某维度时不赠送对应分数；无正向偏好或零分项不推荐。
这是一套可解释的初始策略，不是实测概率，也未经过用户数据校准。

可选 `preference["priority_weights"]` 为 location/category/keyword 的权重乘数，
范围 0–3，默认 1；乘完后归一到 100，按最大余数法分配到小数点后两位。
无效值按 1 处理，全零回退默认值。显式提高 keyword 权重可使关键词匹配更重要。
Input Agent 当前不生成该可选字段，由直接调用方提供；列表顺序不隐含优先级。

```python
preference["priority_weights"] = {"keyword": 3}
```

## Priority Score

`priority_score = 0.8 × match_score + deadline_bonus + freshness_bonus`，范围 0–100。
保留 80% 给匹配，20% 给时效，避免 100 分匹配项加分后全被截成 100，失去时效差异。

| 因素 | 规则 | 加分 |
|---|---|---:|
| 截止紧迫度 | 今天至 3 天内 / 4–7 天 / 8–14 天 / 更远 | 10 / 6 / 3 / 0 |
| 新鲜度 | 发布距今 0–7 天 / 8–30 天 / 更久 | 10 / 5 / 0 |

日期按天计算，不解析具体截止时刻。默认使用 UTC+8 的当天；测试或重放可传
`as_of=date(2026, 10, 4)`。同一业务日期、相同输入结果固定；日期改变可改变优先级。
缺失或非法日期不加分，未来发布时间不加分，也没有发布时间排序优势。
不使用 `last_updated` 作为发布时间，避免数据库读取导致虚假新鲜度。
已截止项保留匹配分，但 priority 归零并标记 `deadline_expired=True`；并未删除记录，
未来真正推送的调用方应跳过这些记录。本模块不发送通知、不实现 Scheduler。

## Why Recommended 与 Final Rank

- `why_recommended` 仅解释 Match Score，加分之和等于 `match_score`。
- `priority_reasons` 解释匹配折算、截止、新鲜度及过期抵扣，之和等于 `priority_score`。
- `score_breakdown` 提供上述两组机器可读分项。分数保留两位小数，浮点核对用容差。
- 排序：priority 降序 → match 降序 → deadline 升序（未知最后）→ published_at 降序
  （未知/未来最后）→ job_id（无则 item_id）升序 → 完整结果的稳定 JSON 文本。
- `final_rank` 从 1 连续编号。相同 ID 也有稳定的内容决胜规则，不依赖输入顺序。

## Exclude Logic

明确排除的词在标题、机构、类别、摘要、标签或资格要求中出现，直接过滤。
排除“销售”会展开为销售、保险代理、电话营销、地推、客服销售；不会因其他维度高分
重新进入结果。旧 `why_recommended` 不参与排除或关键词计算。
此为保守的子串规则，可能误杀“非销售”等否定描述；未实现语义否定或同义词模型。

## Feedback Hook 与限制

预留 keyword-only 参数 `user_feedback_weights=None`。当前传值只记录 INFO 提示，
**不调整分数**；TODO：后续定义反馈字段、幅度与回归测试后再启用。不保存用户记忆，
不实现学习算法。未来 LLM 如加入，仅可辅助语义相似度或解释，不控制最终评分。

真实网站的未知日期可能排在已知日期之后，优先级高不等于具备申请资格。
年龄、专业资格、语言翻译及个性化学习均不在本版范围。

运行：`python -m unittest discover -s tests -v`。
原有测试保留不变，新增测试覆盖规则、边界、确定性、输入保护及分项核对。
