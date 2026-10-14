# Retrieval / Database

`get_items(preference)` 支持 `mock`（默认）、`database`、`web` 三种模式，通过环境变量
`BRIEFFLOW_RETRIEVAL_MODE` 切换。所有来源都经过规范化、校验和确定性去重。

## 来源（web 模式）

六个公开来源，单源失败不影响其他来源：

| 来源 | 类别 | 抓取方式 |
|---|---|---|
| UKRI 科研资助 RSS | 科研机会 | RSS（xml） |
| 挑战杯官网「挑战杯动态」 | 经管比赛 | HTML 列表 + 最多 3 个详情页 |
| 中国金融期货交易所「中金所杯」 | 经管比赛 | HTML 列表 + 最多 3 个详情页 |
| 香港交易所 Early Careers | 金融实习 | 固定官方页面，只截取 Summer Internship 段 |
| 澳门政府新闻局 | 大学生/青年竞赛 | 官方 RSS + 官方详情，遵守 20 秒 crawl-delay |
| 香港证监会实习 | 金融实习 | 两个固定官方项目页；只输出明确且未过期截止日 |

## 日期

- `published_at`：来源提供的发布时间（UKRI 的 pubDate、中金所的列表日期）。
- `deadline`：`extract_deadline(text)`（`backend/retrieval/dates.py`）从详情正文提取，只认
  「截止/截至」或明确「报名时间……至……」中的完整年份日期；缺年份或同一语义片段
  多日期冲突时返回空，不猜测。
- 详情页失败时保留列表记录并写 `detail_failed` 警告；不会用标题或抓取日期伪造截止日期。
- 澳门详情只写月日时，只有 RSS 提供发布日期才使用同年；跨年不猜测。HKEX/SFC 支持页面实际使用的英文月份截止语句。

## 已知待办

- UKRI、挑战杯、中金所等全国/国际来源仍使用 `location="未注明"`，会受 Ranking 地点硬过滤；
  HKEX/SFC 明确为香港、澳门政府源明确为澳门，因此四城查询可命中这些区域来源。
- 当前 SQLite 是团队 V0.1 兼容缓存，不包含本地原型里的 Alembic 修订链和业务实体表；
  正式数据库契约仍需 M1/M3/M4 评审，不能把两套 DDL 并行合并。

运行 `python -m backend.retrieval --mode mock` 输出 JSON 与采集统计。
详见 [RETRIEVAL_DATABASE.md](../../docs/RETRIEVAL_DATABASE.md)。
