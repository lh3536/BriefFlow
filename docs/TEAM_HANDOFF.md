# BriefFlow V0.1 Team Handoff

当前所有流水线模块只是 V0.1 Skeleton，使用规则和本地 Mock Data 完成接口联调。
目录按产品流程组织，不按团队成员命名。

| Owner | 负责范围 | 后续接手方向 |
|---|---|---|
| AI Agent Owner | `backend/input_agent` + `backend/output_agent` | 输入理解、结构化 Preference、最终结果整合 |
| Retrieval Owner | `backend/retrieval` | Database、Web Retrieval、Crawler |
| Ranking Owner | `backend/ranking` | Ranking、Priority、Personalized Delivery |
| Main / Frontend Owner | `backend/router` + `backend/main.py` + `frontend` | 主程序、Router、Frontend |
| Product / Data / Business Owner | `data` + `finance` + product validation | 产品、数据、商业模型、测试与文档 |

每个 Owner 后续需要：

1. **Read**：阅读负责模块及 [ARCHITECTURE.md](ARCHITECTURE.md) 的接口约定。
2. **Run**：实际运行验证、测试和 `python backend/main.py`。
3. **Understand**：理解输入、输出、固定规则、错误行为和未实现范围。
4. **Improve**：在后续确认的任务范围内逐步替换占位实现；接口变化需协调上下游。
5. **Test**：覆盖正常流程、无结果和异常情况，并运行全部已有测试。

不要直接相信 AI 生成的代码。请人工阅读、验证规则，并用测试确认行为。

本次交付没有接入真实 LLM、Crawler、数据库、完整 React 页面、Authentication、
Payment、Email、复杂 Recommendation Model 或 Scheduler。以上方向不属于本次实现。

## D11 新类别契约同步（2026-10-15）

Retrieval 已适配六个新类别：UKRI 输出由 `科研机会` 改为 `科研`；测试 fixture、20 条
Mock Data 断言和 SQLite 缓存字段同步更新。SQLite 会兼容升级旧缓存，新增 `module`、
`disciplines`、`grades`、`time_pref`，其中列表字段继续按 JSON 文本保存并回读。

实测 `pytest tests/test_retrieval.py -q` 为 `29 passed, 11 subtests passed`，Mock 数据校验
为 `PASS`。PR #4 仍需 A0 Owner 输出新类别，并由 Ranking Owner 处理其分支与当前 `dev`
的 RC2 评分冲突；在这两项完成且全仓测试通过前，不应合入 `dev`。
