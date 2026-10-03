# BriefFlow Unit Economics

ASSUMPTION / 待验证：全部输入为占位假设，计算结果也不是实测数据。

LOW / BASE / HIGH 表示商业表现情景；每用户指全部月活用户（含免费用户）。
月成本按各情景月活及运行频次计算；架构间仅改变 Token 用量，其余条件相同。
金额为人民币。盈亏平衡人数向上取整；非正贡献毛利返回 None 并警告。

| Metric | Low | Base | High | Source / Status |
|---|---:|---:|---:|---|
| Pro Price (RMB/month) | 19.00 | 29.00 | 39.00 | 假设值，待验证 |
| Paid Conversion Rate | 3.0% | 8.0% | 12.0% | 假设值，待验证 |
| Full LLM Tokens / Run | 12,000.00 | 10,000.00 | 8,000.00 | 假设值，待验证 |
| Modular Tokens / Run | 7,200.00 | 4,000.00 | 2,000.00 | 假设值，待验证 |
| Module Replacement Ratio | 40.0% | 60.0% | 75.0% | 假设值，待验证 |
| LLM Cost / 1M Tokens (RMB) | 20.00 | 15.00 | 10.00 | 假设值，待验证 |
| Search/API Cost (RMB/run) | 0.03 | 0.02 | 0.01 | 假设值，待验证 |
| Storage/Bandwidth (RMB/user/month) | 0.00 | 0.00 | 0.00 | 假设值，待验证 |
| Notification (RMB/user/month) | 0.05 | 0.03 | 0.02 | 假设值，待验证 |
| Server (RMB/month) | 100.00 | 60.00 | 30.00 | 假设值，待验证 |
| Domain (RMB/year) | 120.00 | 120.00 | 120.00 | 假设值，待验证 |
| Runs / User / Month | 8.00 | 6.00 | 4.00 | 假设值，待验证 |
| Monthly Active Users | 100.00 | 300.00 | 600.00 | 假设值，待验证 |
| Variable Cost / User — Full (RMB/month) | 2.21 | 1.05 | 0.38 | 假设值，待验证 |
| Variable Cost / User — Modular (RMB/month) | 1.44 | 0.51 | 0.14 | 假设值，待验证 |
| ARPU (RMB/month) | 0.57 | 2.32 | 4.68 | 假设值，待验证 |
| Contribution Margin — Full (RMB/user/month) | -1.64 | 1.27 | 4.30 | 假设值，待验证 |
| Contribution Margin — Modular (RMB/user/month) | -0.87 | 1.81 | 4.54 | 假设值，待验证 |
| Fixed Cost (RMB/month, server + domain/12) | 110.00 | 70.00 | 40.00 | 假设值，待验证 |
| Break-even Users — Full | 无法达到盈亏平衡 | 56.00 | 10.00 | 假设值，待验证 |
| Break-even Users — Modular | 无法达到盈亏平衡 | 39.00 | 9.00 | 假设值，待验证 |
| Token Saving Rate | 40.0% | 60.0% | 75.0% | 假设值，待验证 |
| Monthly Cost — Full (RMB) | 331.00 | 385.00 | 268.00 | 假设值，待验证 |
| Monthly Cost — Modular (RMB) | 254.20 | 223.00 | 124.00 | 假设值，待验证 |
| Monthly Cost Saving (RMB) | 76.80 | 162.00 | 144.00 | 假设值，待验证 |
| Contribution Margin Difference (RMB/user/month) | 0.77 | 0.54 | 0.24 | 假设值，待验证 |

确定性 Python 负责日期判断、关键词过滤、去重、基础排序、规则匹配、网页格式化和静态生成；LLM 负责自然语言理解、语义分类、语义匹配、摘要和解释。替代比例是待测假设，并非已实现或已测性能。

MVP 假设 GitHub Pages 存储/带宽变量成本为零；LLM 单价是输入/输出混合占位单价，不是供应商报价。未包含人工、获客、税费、支付手续费；此处盈亏平衡仅覆盖列出的技术成本。

2026-10-07 测试后更新：价格接受度、付费意愿与后续实际转化率、月活与使用频次、两种架构 Token 和质量、API 调用费用、通知费用、存储带宽、服务器与域名成本。单日测试不能证明长期转化率或月度留存。
