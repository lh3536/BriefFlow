# Retrieval 复用记录

本文件只记录 Retrieval/Data 本轮实际复用的现有组件，避免另建通用框架。

| 能力 | 复用 | 本轮边界 |
|---|---|---|
| HTTP | 项目已有 `urllib.request` 白名单请求 | 沿用现有超时、响应上限和 host 校验；未新增 HTTP 客户端 |
| RSS/XML | 标准库 `xml.etree.ElementTree` | 仅解析已确认的 UKRI RSS；拒绝 DTD/ENTITY 和超限响应 |
| HTML | 项目已有 `html.parser.HTMLParser` | 只做挑战杯/中金所详情页的可见文本薄适配，不建立通用爬虫框架 |
| 日期 | `backend/retrieval/dates.py` | 只接受有截止语义和完整年份的证据，不猜年份 |
| 数据库 | 项目已有参数化 `sqlite3` 存储 | 本 PR 保持 V0.1 兼容；正式迁移/修订表待共享契约评审 |

本地 SQLAlchemy/Alembic 原型已完成独立验证，但未直接复制进团队仓库，原因是团队当前
运行时依赖与 DDL 尚未批准。后续只能选择一条正式迁移链，不能让 sqlite3 表与 Alembic
模型作为两个权威定义并行演化。
