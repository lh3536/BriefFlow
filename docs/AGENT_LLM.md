# AO Agent LLM 增强说明（第二轮）

> 适用范围：`backend/input_agent` + `backend/output_agent`（AO：理解用户输入 + 输出整合）。
> 本文档补充 `input_output_changes.md`；原有 Preference / Item 契约不变，Output 契约**新增 `summary_mode` 字段**用于标识摘要来源。

## 设计：规则为底，LLM 增强

V0.1 的规则解析器是**唯一基线**，永远可用（无网、无 Key、无第三方依赖）。
LLM 只是可选增强：配置了 `BRIEF_LLM_API_KEY` 才启用，任何环节失败都自动回退规则路径。

```
用户输入
  ├─ 规则解析（永远执行，结果保底）
  └─ LLM 解析（有 Key 才执行）
        ├─ 成功且通过校验 → 与规则结果并集合并
        └─ 失败/超时/乱输出 → 丢弃，重试 1 次，仍失败则只用规则
```

### Input Agent（理解用户输入）

- `parse_user_request(text)` 签名、返回结构不变（四个字符串列表字段）。
- LLM 输出先经 JSON 提取（容忍 ```json 包裹）→ `validate_preference()` 校验：
  - 只接受四个契约字段，多余字段丢弃；
  - `categories`/`locations` 只保留词表内值（金融实习/经管比赛/夏令营/科研机会、
    广州/深圳/香港/澳门），LLM 编造的值直接过滤，避免打穿下游硬筛选；
  - 只保留 ≤20 字的字符串，每个字段最多 10 项，自动去重。
- 合并策略是**并集**：规则识别的条件永远不会被 LLM 弄丢，LLM 只能补充规则漏掉的表达
  （例如"行研""打杂"这类词表外说法）。
- 空白输入不调用 LLM，直接返回四个空列表；非字符串输入仍然 `ValueError`。

### Output Agent（输出整合）

- `build_brief(preference, ranked_items)` 签名及原有四个字段保留
  （preference / total_items / recommended_items / summary），新增 summary_mode 标识实际摘要来源。
- 确定性摘要永远先算好（"本次找到 N 条匹配，其中 M 条高度匹配"），作为兜底。
- 有 Key 时用 LLM 写更自然的摘要，校验通过（非空、≤120 字、不含 JSON/Markdown 残渣）才采用；
  失败重试 1 次后回退确定性摘要。
- **LLM 不参与排序、不改分数**；推荐记录照旧深复制、不重排、不截断。

## 配置

复制 `.env.example` 为 `.env`，填入 Key 即可（四个变量见文件注释）。
`.env` 已在 `.gitignore`。**没有 Key 时整个系统行为与 V0.1 完全一致。**

实现上不新增任何第三方依赖：LLM 调用用标准库 `urllib` 直连 OpenAI 兼容接口
（`backend/llm.py`，AO 两个 Agent 共用）。

## 验证

```sh
# 全部测试（含 LLM mock 测试，不联网）
python3 -m unittest discover -s tests -v

# 无 Key：与 V0.1 完全一致
python3 backend/main.py

# 有 Key：LLM 自动增强
export BRIEF_LLM_API_KEY=sk-...
python3 backend/main.py
```

LLM 路径的测试全部 mock（`tests/test_agent_llm.py`），不联网、不需要 Key，
覆盖：合并、校验过滤、噪声 JSON 提取、失败重试、回退、不变异输入数据、
空白输入不调用、契约字段形状。

## 已知边界（下一轮再说）

- 并集策略下 LLM 无法"纠正"规则误识别（如规则把"客服经验分享会"误判为排除客服）。
- Token 用量尚未接入统计（等 Nolan 的编排器/AgentRun 接口后对接）。
- 输出摘要的语言风格、是否分条，待与 Nolan 前端确认展示形态后再调。

## 配置补充

新增可选环境变量：
- `BRIEF_LLM_TEMPERATURE`：可选；默认不传；若设置则作为模型 temperature 参数。
  注意 kimi-k2.6 等部分模型只接受 `1`，传 `0` 会报 400。

## Streamlit integration demo

Install Python 3.10+ dependencies and run from the repository root:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

No FastAPI server is needed. Root `app.py` calls `backend.router.service.run_brief_flow`
directly. React and FastAPI remain available as historical Web/API interfaces.
Copy `.env.example` to `.env` to configure the optional LLM. Never commit `.env`.
The sidebar shows configuration availability; `summary_mode` (`llm` or
`deterministic`) is additive output metadata identifying the actual summary source.
The original four result fields remain intact. Input rules always run, and valid
LLM preferences are merged with them. Output LLM changes only summary text.

Retrieval defaults to mock. Mock results are visibly labeled, including existing
web/database fallback. Cards retain source labels. Pipeline exceptions display an
error and clear stale results. The former feedback button was removed because no
feedback learning is implemented; it must not claim to update ranking memory.

Run all checks (LLM transport is mocked in tests):

```sh
python -m pip install -r backend/requirements.txt pytest
python -m pytest -q
python data/validation/validate_mock_data.py
cd frontend
npm ci
npm test
npm run build
```
