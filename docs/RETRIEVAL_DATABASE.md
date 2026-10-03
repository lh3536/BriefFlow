# Retrieval / Database V0.1

流程：Data Source → Fetch → Normalize → Validate → Deduplicate → Return Items。
Router 继续调用 `get_items(preference)`，不需要知道来源；偏好筛选与评分仍属于 Ranking。
实现仅用 Python 标准库，不需要 API Key 或额外框架。

## 来源与模式

| 模式 | 数据来源 | 行为 |
|---|---|---|
| `mock`（默认） | `data/mock/mock_db.json` | 离线读取现有 15 条 Mock Data，不写数据库 |
| `web` | [UKRI 官方 Funding Finder RSS](https://www.ukri.org/opportunity/feed/) | 一次公开请求，清洗后自动写入 SQLite，再返回结果 |
| `database` | 本地 SQLite `items` 表 | 读取已有记录，重新校验和去重；不请求网络 |

UKRI 来源页面：[Funding finder](https://www.ukri.org/opportunity/)。它发布科研资助机会，
不是粤港澳实习源，也不代表本科生有申请资格。仅接入这个 RSS，不抓详情页，不分页，
不登录，不绕过验证码或付费墙。每次最多 20 条、2 MB，网络超时 15 秒，无自动重试。

2026-10-03 实际抓取返回 HTTP 200、20 条记录。离线解析样本保存在
`tests/fixtures/ukri_excerpt.xml`，含本次响应前两条的标题、链接、发布时间；
说明见同目录 `ukri_excerpt_README.md`。测试不依赖实时网络，也不会将样本当成最新数据。
本次实测 Web 接收 20 条、SQLite 读回 20 条，`科研机会` 经 Router 返回 20 条；未触发 Mock 回退。

Web/DB 读取失败、空结果或全部记录被拒绝时，记录原因并回退到 Mock；来源明确标为
`BriefFlow Mock`。Mock 本身损坏且无法恢复时返回空列表。数据库写入失败时保留本次
有效 Web 结果并记录警告。回退的 Mock 不混入 Web 数据库。

## 接口与结构

`normalize_item(raw_item)` 返回以下标准原始字段；`validate_item(item)` 返回错误列表：

```text
item_id, title, organization, location, category, summary,
source, source_url, published_at, deadline, tags, requirements, last_updated
```

- `tags`、`requirements` 为字符串列表；日期为 `YYYY-MM-DD`，未知日期为空字符串。
  `last_updated` 为 ISO 时间戳，表示本地获取/规范化时间，不是来源修改时间。
- UKRI 的 `title/link/pubDate/description` 映射为 `title/source_url/published_at/summary`。
  HTML 描述转纯文本。organization 为发布机构 UKRI，未细分实际资助委员会。
- 该源统一归类为“科研机会”，用“科研资助”标签标明子类型；不伪造招聘岗位。
  RSS 未提供结构化地点、deadline 或资格，分别保留“未注明”、空字符串、空列表。
  空资格列表代表尚未提取，不代表任何人均可申请。需查看原链接。
- 标题、机构、来源必须非空；URL 须为无凭据的公开 HTTP(S) 地址；类别限定为现有
  四类；地点为 1–100 字符纯文本；已填写日期必须有效。无效记录跳过并记录原因。
- ID 优先保留现有 `job_id/item_id`，否则按规范化 URL 生成稳定 SHA-256 摘要 ID。

`get_items(preference)` 返回同一标准字段集，并附加兼容字段：
`job_id = item_id`、`company = organization`、`link = source_url`、
`match_score = 0`、`why_recommended = []`。后两项仅占位，Ranking 负责计算。
Mock 文件中的旧分数不作为 Retrieval 原始数据；磁盘 Mock 文件完全不变。

这是一项**新增字段的兼容扩展**：原字段名和 Router 调用不变。原 Pipeline 中唯一
“字段集合必须恰好九项”的 Retrieval 断言改为检查旧字段全部存在及新增来源字段，
其余模块代码与测试行为保留。

## SQLite 与去重

默认文件：`backend/retrieval/.cache/items.sqlite3`，首次 Web 抓取成功时创建。
可通过 `BRIEFFLOW_DB_PATH` 指定位置。缓存及 SQLite 文件由 Retrieval 局部 `.gitignore`
排除，不提交运行数据库。

`items` 表包含上述 13 个标准字段及 `content_key`；列表存为 JSON 文本。
`item_id` 为主键，`source_url` 和 `content_key` 各有唯一约束。
没有 `match_score`、`why_recommended` 列。`save_items(items, path)` 校验后用参数化 SQL
按 URL upsert，保留既有 ID；`load_items(path)` 读回记录，由公共流水线再次校验。

单次抓取按规范化 URL、ID 或标题+机构+deadline 去重，保留第一条。
URL 去掉 fragment、`utm_*`/`fbclid`/`gclid`，保留其他查询参数。
内容键做空白合并和大小写归一化。SQLite 的唯一约束同时阻止跨批次内容重复；
冲突或无效写入逐条记录后跳过，不中断其他记录。

## 运行与日志

在仓库根目录运行：

```sh
python -m backend.retrieval --mode mock
python -m backend.retrieval --mode web
python -m backend.retrieval --mode database
python -m backend.retrieval --mode database --db-path /path/to/items.sqlite3
python -m unittest discover -s tests -v
python data/validation/validate_mock_data.py
```

Router 可通过环境变量 `BRIEFFLOW_RETRIEVAL_MODE=mock|database|web` 切换，默认为 mock。
命令行工具把 Items JSON 写到 stdout，标准 logging 写到 stderr；其他调用方可用
`logging.basicConfig(level=logging.INFO)` 开启统计。每次来源尝试记录：
`source`、`mode`、`items_fetched`、`items_accepted`、`items_rejected`、
`duplicates_removed`、`duration`（秒）、`status`。回退会额外记录 Mock 尝试。
计数针对本次读取的数据，accepted 为去重后数量；数据库跨批次冲突另有逐条日志。

## 扩展与限制

增加来源时在 `sources.py` 加公开数据适配器，输出标准原始字段，然后接入同一清洗路径；
同时补充真实响应 fixture、无效记录与网络故障测试。不要把网站专有字段传给 Router。
不需要改 Ranking 或 Input/Output Agent。

本版无调度、数据库迁移、过期记录清理、详情页资格解析或语言翻译。
DB 可包含历史记录，Web feed 也可能包含已截止/邀请制机会；未判断是否可申请。
未注明地点的 UKRI 数据会被当前指定四城的 Ranking 筛选掉，这是现有规则的正常行为。
可用 `run_brief_flow("科研机会")` 演示真实数据全流程，结果仍须查原文资格。
受限词表与去重规则可能合并同名机会，后续优化应由相应 Owner 评审。
