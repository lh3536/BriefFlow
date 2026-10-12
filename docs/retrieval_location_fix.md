# Retrieval 第二轮：location 硬过滤修复方案（给 Ranking Owner / Flin）

## 问题（已实测）

真实来源（UKRI 科研资助、挑战杯、中金所杯）多为**全国/国际性**，没有单一城市，
Retrieval 因此把 `location` 写成 `"未注明"`。而 Ranking 的 `rank_items` 对 location
做**硬过滤**：

```python
if locations and item.get("location") not in locations:
    continue
```

实测：用户指定城市（广州/深圳/香港/澳门，demo 默认就是）时，`location="未注明"`
的真实条目 **0 条通过**，导致 web 模式跑真实数据时一条推荐都出不来。

## 建议修复（最小改动，只需改 Ranking）

引入一个「不受城市约束」的哨兵值 `"未注明"`，Ranking 遇到它时**跳过 location 硬过滤**
（即全国性来源对任意城市都放行，但 category/keyword/exclude 仍照常过滤）：

```python
# backend/ranking/service.py
UNCONSTRAINED_LOCATION = "未注明"  # 与 retrieval 约定一致

# 在硬过滤处改为：
if locations and item.get("location") not in locations \
        and item.get("location") != UNCONSTRAINED_LOCATION:
    continue
```

需要同时确认：`"未注明"` 这个字面值作为约定，两个模块共用（建议放公共常量，
或至少在双方 README 里写死）。若 Flin 更希望用别的哨兵（如空串 `""` 或 `"全国"`），
以他定的为准，Retrieval 这边跟着改。

## 不改 Ranking、只改 Retrieval 的备选（不推荐）

把全国性来源硬写成某个城市（如「广州」）——不诚实，会误导评分理由，不采用。
