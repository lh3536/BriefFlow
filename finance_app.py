"""BriefFlow 财务系统：三级付费单位经济模型 + 成本统计仪表盘（独立应用）。

三级定价与 backend/tiers.py 一致：Free ¥0 / Plus ¥19 / Pro ¥39。
全部输入为 ASSUMPTION / 待验证；LOW/BASE/HIGH 表示商业表现情景。
金额为人民币。
"""
import streamlit as st
from math import ceil

st.set_page_config(page_title="BriefFlow 财务系统", layout="wide")

PLUS_PRICE = 19.0
PRO_PRICE = 39.0

_BASE_CSS = """
<style>
:root {
    --bg: #ffffff; --bg-panel: #ffffff; --text: #111827; --muted: #6b7280;
    --line: #e5e7eb; --border: #111827; --blue: #2563eb; --gold: #b8860b;
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background: var(--bg); }
.block-container { padding-top: 2rem; max-width: 1180px; }
h1, h2, h3, [data-testid="stHeading"] h1, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3 {
    color: var(--text) !important; letter-spacing: -0.02em;
}
.stMarkdown p, label, [data-testid="stCaptionContainer"] p { color: var(--text); }
[data-testid="stMetric"] {
    border: 1.5px solid var(--border); border-radius: 12px; padding: 0.5rem 0.85rem; background: var(--bg-panel);
}
[data-testid="stMetricValue"] { color: var(--text); font-size: 1.4rem; }
[data-testid="stMetricLabel"] { color: var(--muted); }
[data-testid="stSidebar"] { background: var(--bg); border-right: 1px solid var(--line); }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: var(--text); }
.brand-brief { color: #38bdf8; }
.brand-flow { color: #1e3a8a; }
</style>
"""
st.markdown(_BASE_CSS, unsafe_allow_html=True)

st.markdown(
    '<h1><span style="font-style:italic;"><span class="brand-brief">Brief</span><span class="brand-flow">Flow</span></span> · 财务系统</h1>',
    unsafe_allow_html=True,
)
st.caption("三级付费单位经济模型 · 全部输入为假设值，待验证 · 金额单位：人民币（元）")


# 三情景假设参数（成本项沿用 finance/stats.py 的占位假设）
SCENARIOS = {
    "low": {
        "label": "保守 (Low)",
        "plus_conversion": 0.02, "pro_conversion": 0.01,
        "llm_tokens_per_run": 12000, "llm_rmb_per_million": 20.0,
        "search_api_per_run": 0.03, "notification_per_user": 0.05,
        "storage_per_user": 0.0, "server_per_month": 100.0, "domain_per_year": 120.0,
        "runs_per_user_month": 8, "mau": 100,
    },
    "base": {
        "label": "基准 (Base)",
        "plus_conversion": 0.05, "pro_conversion": 0.03,
        "llm_tokens_per_run": 10000, "llm_rmb_per_million": 15.0,
        "search_api_per_run": 0.02, "notification_per_user": 0.03,
        "storage_per_user": 0.0, "server_per_month": 60.0, "domain_per_year": 120.0,
        "runs_per_user_month": 6, "mau": 300,
    },
    "high": {
        "label": "乐观 (High)",
        "plus_conversion": 0.07, "pro_conversion": 0.05,
        "llm_tokens_per_run": 8000, "llm_rmb_per_million": 10.0,
        "search_api_per_run": 0.01, "notification_per_user": 0.02,
        "storage_per_user": 0.0, "server_per_month": 30.0, "domain_per_year": 120.0,
        "runs_per_user_month": 4, "mau": 600,
    },
}


def compute(p: dict) -> dict:
    """按三级定价计算单位经济指标。"""
    llm_cost_per_run = p["llm_tokens_per_run"] * p["llm_rmb_per_million"] / 1_000_000
    run_cost = llm_cost_per_run + p["search_api_per_run"]
    variable_per_user = (
        run_cost * p["runs_per_user_month"]
        + p["notification_per_user"] + p["storage_per_user"]
    )
    arpu = PLUS_PRICE * p["plus_conversion"] + PRO_PRICE * p["pro_conversion"]
    fixed = p["server_per_month"] + p["domain_per_year"] / 12
    total_cost = fixed + variable_per_user * p["mau"]
    total_revenue = arpu * p["mau"]
    contribution = arpu - variable_per_user
    break_even = ceil(fixed / contribution) if contribution > 0 else None
    return {
        "llm_cost_per_run": llm_cost_per_run,
        "variable_per_user": variable_per_user,
        "arpu": arpu,
        "fixed": fixed,
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "profit": total_revenue - total_cost,
        "break_even": break_even,
        # 成本项拆分（每月，用于结构图）
        "cost_llm": llm_cost_per_run * p["runs_per_user_month"] * p["mau"],
        "cost_search": p["search_api_per_run"] * p["runs_per_user_month"] * p["mau"],
        "cost_notify": p["notification_per_user"] * p["mau"],
        "cost_storage": p["storage_per_user"] * p["mau"],
        "cost_server": p["server_per_month"],
        "cost_domain": p["domain_per_year"] / 12,
    }


def monthly_trend(p: dict, months: int = 12) -> list[dict]:
    """假设月活从 0 线性增长到当前值，生成 months 个月的模拟运营数据。"""
    rows = []
    for i in range(1, months + 1):
        mau_m = max(1, int(p["mau"] * i / months))
        mm = compute({**p, "mau": mau_m})
        rows.append({
            "月份": f"M{i}",
            "月活": mau_m,
            "收入": round(mm["total_revenue"], 2),
            "成本": round(mm["total_cost"], 2),
            "净利": round(mm["profit"], 2),
        })
    return rows


# 侧边栏：情景选择 + 可调参数
with st.sidebar:
    st.subheader("情景与参数")
    scenario_key = st.radio(
        "选择情景", list(SCENARIOS.keys()),
        format_func=lambda k: SCENARIOS[k]["label"],
    )
    base = SCENARIOS[scenario_key]
    st.caption("以下参数可覆盖所选情景的默认值：")
    mau = st.number_input("月活用户", 10, 10000, base["mau"], 10)
    plus_conv = st.number_input("Plus 转化率", 0.0, 1.0, base["plus_conversion"], 0.01, format="%.3f")
    pro_conv = st.number_input("Pro 转化率", 0.0, 1.0, base["pro_conversion"], 0.01, format="%.3f")
    with st.expander("成本单价（高级）"):
        llm_tokens = st.number_input("LLM tokens/次", 1000, 50000, base["llm_tokens_per_run"], 1000)
        llm_price = st.number_input("LLM 单价（元/百万 tokens）", 1.0, 100.0, base["llm_rmb_per_million"], 1.0)
        search_api = st.number_input("搜索 API（元/次）", 0.0, 1.0, base["search_api_per_run"], 0.01)
        notify = st.number_input("通知（元/用户/月）", 0.0, 1.0, base["notification_per_user"], 0.01)
        storage = st.number_input("存储/带宽（元/用户/月）", 0.0, 1.0, base["storage_per_user"], 0.01)
        server = st.number_input("服务器（元/月）", 0.0, 1000.0, base["server_per_month"], 10.0)
        domain = st.number_input("域名（元/年）", 0.0, 1000.0, base["domain_per_year"], 10.0)
        runs = st.number_input("运行次数（次/用户/月）", 1, 50, base["runs_per_user_month"], 1)

params = {
    "plus_conversion": plus_conv, "pro_conversion": pro_conv,
    "llm_tokens_per_run": llm_tokens, "llm_rmb_per_million": llm_price,
    "search_api_per_run": search_api, "notification_per_user": notify,
    "storage_per_user": storage, "server_per_month": server, "domain_per_year": domain,
    "runs_per_user_month": runs, "mau": mau,
}
m = compute(params)

st.divider()

# 三级定价说明
c1, c2, c3 = st.columns(3)
for col, name, price, desc in (
    (c1, "Free", "¥0", "按类型单维度 · 5 条 · 历史 5 条"),
    (c2, "Plus", f"¥{PLUS_PRICE:.0f}/月", "类型+地点+专业+年级 · 20 条 · 历史 50 条"),
    (c3, "Pro", f"¥{PRO_PRICE:.0f}/月", "全维度 · 不限条数 · LLM 增强摘要"),
):
    with col:
        st.markdown(
            f'<div style="border:1.5px solid var(--border);border-radius:12px;padding:0.8rem 1rem;background:var(--bg-panel);">'
            f'<div style="font-weight:800;font-size:1.1rem;color:var(--text);">{name}</div>'
            f'<div style="font-weight:800;font-size:1.3rem;color:var(--blue);">{price}</div>'
            f'<div style="font-size:0.85rem;color:var(--muted);">{desc}</div></div>',
            unsafe_allow_html=True,
        )

st.subheader("核心指标")
m1, m2, m3, m4 = st.columns(4)
m1.metric("月总收入", f"¥{m['total_revenue']:,.2f}")
m2.metric("月总成本", f"¥{m['total_cost']:,.2f}")
m3.metric("月净利", f"¥{m['profit']:,.2f}")
m4.metric("盈亏平衡用户数", "—" if m["break_even"] is None else f"{m['break_even']} 人")
st.caption(f"当前月活 {mau} 人 · ARPU ¥{m['arpu']:.2f} · 每用户变动成本 ¥{m['variable_per_user']:.4f}")

st.subheader("成本结构（每月，按当前参数）")
cost_items = {
    "LLM Token": m["cost_llm"],
    "搜索 API": m["cost_search"],
    "通知": m["cost_notify"],
    "存储/带宽": m["cost_storage"],
    "服务器": m["cost_server"],
    "域名": m["cost_domain"],
}
st.bar_chart(cost_items)
st.caption("LLM Token 通常为最大变动成本项；MVP 假设存储/带宽为 0（GitHub Pages）。")

st.subheader("成本明细（当前参数，每月）")
cost_total = m["total_cost"] or 1.0
cost_detail = [
    ("LLM Token（可变）", m["cost_llm"]),
    ("搜索 API（可变）", m["cost_search"]),
    ("通知（可变）", m["cost_notify"]),
    ("存储/带宽（可变）", m["cost_storage"]),
    ("服务器（固定）", m["cost_server"]),
    ("域名（固定）", m["cost_domain"]),
]
cost_rows = [
    {"成本项": name, "金额(¥)": f"{val:,.2f}", "占比": f"{val / cost_total:.1%}"}
    for name, val in cost_detail
]
cost_rows.append({"成本项": "合计", "金额(¥)": f"{m['total_cost']:,.2f}", "占比": "100%"})
st.table(cost_rows)

st.subheader("收入拆分（当前参数，每月）")
plus_revenue = PLUS_PRICE * plus_conv * mau
pro_revenue = PRO_PRICE * pro_conv * mau
st.bar_chart(
    {"来源": ["Plus", "Pro"], "金额(¥)": [round(plus_revenue, 2), round(pro_revenue, 2)]},
    x="来源", y="金额(¥)",
)
st.caption(f"Plus 收入 ¥{plus_revenue:,.2f}（转化 {plus_conv:.1%}）· Pro 收入 ¥{pro_revenue:,.2f}（转化 {pro_conv:.1%}）")

st.subheader("月度运营趋势（12 个月模拟）")
trend = monthly_trend(params)
trend_labels = [r["月份"] for r in trend]
st.line_chart(
    {
        "月份": trend_labels,
        "收入(¥)": [r["收入"] for r in trend],
        "成本(¥)": [r["成本"] for r in trend],
        "净利(¥)": [r["净利"] for r in trend],
    },
    x="月份",
)
st.caption("模拟假设：月活从 0 线性增长到当前值；收入、成本随月活同步变化。")

st.subheader("三情景对比（使用各情景默认假设）")
labels = [SCENARIOS[k]["label"] for k in SCENARIOS]
for metric_label, key in (
    ("月收入(¥)", "total_revenue"),
    ("月成本(¥)", "total_cost"),
    ("月净利(¥)", "profit"),
):
    values = [compute(SCENARIOS[k])[key] for k in SCENARIOS]
    st.bar_chart({"情景": labels, metric_label: values}, x="情景", y=metric_label)
    st.caption(metric_label)

st.divider()
st.caption("说明：金额为人民币；全部输入为占位假设（ASSUMPTION），非实测数据。盈亏平衡仅覆盖列出的技术成本，未含人工、获客、税费、支付手续费。")
