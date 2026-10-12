# Retrieval / Database

`get_items(preference)` 支持 `mock`（默认）、`database`、`web` 三种模式，通过环境变量
`BRIEFFLOW_RETRIEVAL_MODE` 切换。所有来源都经过规范化、校验和确定性去重。

## 来源（web 模式）

三个公开来源，单源失败不影响其他来源：

| 来源 | 类别 | 抓取方式 |
|---|---|---|
| UKRI 科研资助 RSS | 科研机会 | RSS（xml） |
| 挑战杯官网「挑战杯动态」 | 经管比赛 | HTML 列表 |
| 中国金融期货交易所「中金所杯」 | 经管比赛 | HTML 列表 |

## 日期

- `published_at`：来源提供的发布时间（UKRI 的 pubDate、中金所的列表日期）。
- `deadline`：`extract_deadline(text)`（`backend/retrieval/dates.py`）从正文提取，只认
  「截止/截至」+ 带年份的完整日期，缺年份/多日期冲突一律返回空、不猜测。当前列表级
  抓取无正文，deadline 暂为空；接入详情页抓取后即可生效。

## 已知待办

- 真实来源多为全国/国际性，`location` 写成 `"未注明"`；Ranking 目前对 location 做硬过滤，
  指定城市时会全量过滤掉真实条目（见 `docs/retrieval_location_fix.md`，待 Ranking Owner 确认）。

运行 `python -m backend.retrieval --mode mock` 输出 JSON 与采集统计。
详见 [RETRIEVAL_DATABASE.md](../../docs/RETRIEVAL_DATABASE.md)。
