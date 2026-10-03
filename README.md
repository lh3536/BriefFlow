# BriefFlow

AI-powered personalized intelligence brief service.

Current status:

V0.1
- Mock dataset complete
- Data validation complete
- Unit economics model complete
- Automated finance tests complete
- Frontend pending
- Backend pending
- Agent pending
- Retrieval pending
- Feedback pending

## Project Structure

- `frontend/`: Frontend application.
- `backend/`: Backend services, agent logic and information retrieval.
- `data/`: Mock data, validation and development data tools.
- `feedback/`: User feedback and preference learning.
- `finance/`: Unit economics and cost analysis; generated reports in `finance/outputs/`.
- `tests/`: Automated Python tests.
- `docs/`: Product, architecture and competition documentation.

Run the commands below from the repository root.

---

# BriefFlow MVP 开发数据与成本模型

For development and demonstration only. These are synthetic/mock opportunities and do not represent actual current job postings.

`data/mock/mock_db.json` 全部为 MOCK DATA，机构、机会、日期及评分均为虚构，不是实际招聘、比赛或学术活动信息。各标题及机构名称带有模拟标记，链接统一为 example.com。适配测试画像：中山大学、金融学、大三；四个目标城市均有覆盖。评分是用于联调的规则示例，不是实际 Matching Agent 测量结果；解释分数之和等于 match_score。夏令营是虚构预报名场景，其 deadline 不是活动日期。

`finance/stats.py` 全部商业参数均为 **ASSUMPTION / 待验证**，集中存放于 SCENARIOS。LOW/BASE/HIGH 为商业表现偏低/基准/偏高情景，不是置信区间或真实预测。所有用户分母均为全部月活用户，假设免费与付费用户的平均运行次数相同。

ARPU = 月价 × 付费转化率。单用户月变量成本 =（每次 Token 成本 + 每次 Search/API 成本）× 月运行次数 + 通知 + 存储带宽。月固定成本 = 服务器月费 + 域名年费 / 12。贡献毛利 = ARPU − 变量成本。盈亏平衡人数向上取整；贡献毛利非正时返回 None 并发出 Warning。月成本节约 = 单用户两种架构成本差 × 月活用户数。

GitHub Pages 的零存储/带宽费用仅为 MVP 假设。混合 Token 单价不是实际供应商报价。未计人工、获客、税费、支付手续费，盈亏平衡仅指所列技术成本。模块化节省量是模型假设，不代表已部署优化。

确定性代码适合日期、关键词、去重、基础排序、规则匹配、格式化和静态生成；LLM 留给自然语言理解、语义分类/匹配、摘要与解释。

运行（Python 3.10+，无第三方依赖）：

```sh
python data/validation/validate_mock_data.py
python finance/stats.py
python -m unittest discover -s tests -v
```

报告自动生成至 `finance/outputs/unit_economics_output.md`。2026-10-07 测试后替换运行频次、完整与模块化 Token 及质量、实际 API/通知成本等；价格、付费转化、月活需结合测试及后续运营验证。服务器、域名、带宽参数按实际账单更新。单次测试不能确定长期月度指标。
