# BriefFlow V0.1 Architecture

```text
User Input
↓
Input Agent
↓
Retrieval
↓
Ranking
↓
Output Agent
↓
Router (returns result)
↓
Frontend (pending)
```

Router 实际负责调用整个流水线，最后把 Output Agent 的结果返回给调用方。
当前调用方是 `backend/main.py` 的终端演示；Frontend 尚未实现。

| 模块 | 接口 | 职责 |
|---|---|---|
| Input Agent | `parse_user_request(text)` | 用固定关键词规则提取 Preference |
| Retrieval | `get_items(preference)` | 读取本地 Mock Data，返回全部 15 条记录 |
| Ranking | `rank_items(preference, items)` | 筛选、打分、排序，返回新的记录 |
| Output Agent | `build_brief(preference, ranked_items)` | 整合统一 JSON，不修改分数或顺序 |
| Router | `run_brief_flow(user_text)` | 依次调用上述接口，不实现模块内部逻辑 |
| Main | `python backend/main.py` | 固定示例需求，打印前 5 条推荐 |
| Frontend | `frontend/src/` | 仅预留目录，后续消费统一输出 |

## 数据接口

Preference 的四个字段都是字符串列表；空列表表示该维度没有约束：

```json
{
  "categories": ["金融实习"],
  "locations": ["广州", "深圳", "香港", "澳门"],
  "keywords": ["金融"],
  "exclude_keywords": ["销售"]
}
```

每条信息保留现有字段：`job_id`, `title`, `company`, `location`,
`category`, `deadline`, `link`, `match_score`, `why_recommended`。
Ranking 在返回副本中替换分数和解释；不修改输入记录或磁盘上的 Mock Data。

输出是可用 `json.dumps()` 序列化的 Python 字典：

```json
{
  "preference": {"categories": [], "locations": [], "keywords": [], "exclude_keywords": []},
  "total_items": 0,
  "recommended_items": []
}
```

`total_items` 等于推荐列表长度。无匹配时返回空列表。模块通过标准库 Python
函数调用连接，目前没有 HTTP API、LLM、数据库或网络检索。

## V0.1 规则与边界

- 城市：广州、深圳、香港、澳门；“粤港澳”在本演示中展开为这四个城市。
- 类别：实习 → 金融实习，比赛 → 经管比赛，夏令营 → 夏令营，科研/研究助理 → 科研机会。
  这些映射仅适用于当前 Mock Data，并不支持任意行业。
- 关键词：金融、量化、投行、研究、科技。
- “不要”“排除”“不考虑”引导的片段支持排除销售、客服、保险、地推、电话营销。
  片段结束于中文逗号、句号、分号、问号、感叹号或换行。复杂否定和并列句尚不支持。
- 空输入抛出 `ValueError`；未知词忽略，没有识别到任何正向偏好时不推荐。
  不解析年级、专业资格、日期、截止时间或真实岗位资格。
- 地点与类别为硬筛选；排除词匹配标题、机构或类别即剔除。
- 地点匹配 +40、类别匹配 +40、任一关键词匹配 +20；关键词也仅查标题、机构、类别。
  多个关键词不重复加分。最高 100，分数不是概率。零分记录不推荐。
- 按分数降序，同分按 `job_id` 升序。`why_recommended` 列出实际加分原因。
- Retrieval 暂时不使用 Preference 过滤。文件读取和 JSON 解析错误直接向调用方抛出。
- 所有结果均为模拟信息，原财务模型与 Mock Data 保持不变。

## 运行

Python 3.10+，仅标准库；在仓库根目录运行：

```sh
python data/validation/validate_mock_data.py
python -m unittest discover -s tests -p 'test_stats.py' -v
python -m unittest discover -s tests -p 'test_pipeline.py' -v
python backend/main.py
```
