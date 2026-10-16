# Retrieval Owner 交接报告（2026-10-13）

分支：`feature/retrieval-round2`，目标：`dev`。

## 本轮已适配到团队仓库

- 保持 `get_items(preference) -> list[dict]`、Router 调用和旧 pipeline 字段兼容。
- Web 模式继续使用 UKRI、挑战杯、中金所三个公开白名单来源，单源失败不阻断其他来源。
- 挑战杯和中金所由列表级抓取升级为“列表 + 最多 3 个详情页”；详情请求有 15 秒超时、
  2 MB 响应上限、固定 host 校验和 1 秒间隔。
- 详情正文进入 `summary`；挑战杯从页面证据读取发布时间；截止日期只从明确语义和完整
  年份中确定性提取。缺年份、多日期冲突或无证据时保持空字符串。
- 全国/国际机会继续使用 `location="未注明"`，不伪造广州或其他城市。
- 修复 Round 2 分支旧测试仍 patch `fetch_ukri`、而实现已切到 `fetch_web` 导致的 8 个失败。

## 已有但未直接合并的本地数据能力

数据负责人另有经过 50 个测试验证的 SQLAlchemy/Alembic 原型，包含 RawItem 九字段、
采集运行、正文修订、按 Brief 消费、离线 replay 和 SQLite backup。团队仓库当前采用
标准库 SQLite 单表缓存；在 M1/M3/M4 确认正式业务契约和依赖前，本轮不引入第二套 DDL，
也不把 DRAFT 业务实体写成已完成事实。

## 本轮验收证据

- `pytest tests/test_retrieval.py tests/test_retrieval_round2.py -q`：38 passed，11 subtests passed。
- `pytest tests -q -s`：106 passed，116 subtests passed；仅有一条第三方
  Starlette/httpx deprecation warning。
- 2026-10-13 live 小批量：33 条入库并读回（UKRI 20、挑战杯 12、中金所 1）；
  其中中金所详情确定性提取 deadline `2026-10-31`，挑战杯/中金所前 4 个详情正文长度
  为 1781–5398 字符。没有截止证据的条目保持空值。
- `git diff --check`：通过。

pytest 在工作区临时目录下运行；测试使用 fixture/mock，不把 fixture 当成当日真实抓取。
Live 验收数据库位于本机临时目录，未提交 Git；上述数字来自当轮实际运行。

## 未完成与跨 Owner 阻碍

1. Ranking 仍把“未注明”当普通地点做硬过滤；四城画像可能过滤全部真实全国机会。
   语义需 Ranking Owner 确认，Retrieval 不代改评分规则。
2. 正式数据库迁移、正文 revision 和全业务实体表尚未进入团队仓库；需先冻结共享契约。
3. M3 尚未确认数据库事务/消费确认接口，M4 尚未确认 RawItem 到 InformationItem 的映射。
4. 本轮不实现 REST、LLM、评分、反馈记忆、前端或调度。

## 建议合并顺序

1. Retrieval Owner 检查本 PR 的真实来源、字段和失败语义。
2. Ranking Owner只确认“未注明/全国”如何参与地点过滤，并在自己的分支实现。
3. `feature/retrieval-round2 -> dev` 通过 review 和 CI 后合并。
4. 再单开数据库正式化任务，由数据负责人维护唯一迁移链。
