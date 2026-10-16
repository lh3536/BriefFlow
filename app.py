"""Streamlit demo calls the Python Router directly; no FastAPI server required."""
import os
import re
from datetime import date, datetime
from urllib.parse import urlsplit

import streamlit as st
from backend.router.service import run_brief_flow
from backend.output_agent.presentation import describe_items, is_high_match, deadline_days
from backend.tiers import TIERS, DIM_LABELS

st.set_page_config(page_title="BriefFlow 个人情报站", layout="wide")

# 会话状态初始化
st.session_state.setdefault("history", [])
st.session_state.setdefault("dark_mode", False)
st.session_state.setdefault("tier", "free")
st.session_state.setdefault("upgrade_prompted", False)
st.session_state.setdefault("show_upgrade", False)

# Apple 官网级质感基础样式：微边框 + 弥散投影 + 毛玻璃 + 流体渐变胶囊 + 分段控制器
_BASE_CSS = """
<style>
:root {
    --bg: #fbfbfd;
    --bg-gradient: radial-gradient(1200px 500px at 50% -120px, rgba(0, 113, 227, 0.07), transparent 70%);
    --bg-panel: rgba(255, 255, 255, 0.82);
    --bg-subtle: rgba(245, 245, 247, 0.75);
    --text: #1d1d1f;
    --muted: #86868b;
    --line: rgba(0, 0, 0, 0.06);
    --border: rgba(0, 0, 0, 0.06);
    --border-hover: rgba(0, 113, 227, 0.24);
    --shadow-sm: 0 2px 10px -1px rgba(0, 0, 0, 0.03);
    --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.02);
    --shadow-hover: 0 12px 32px -4px rgba(0, 0, 0, 0.09), 0 2px 8px rgba(0, 0, 0, 0.03);
    --blue: #0071e3;
    --blue-bg: rgba(0, 113, 227, 0.08);
    --btn-blue: #0071e3;
    --btn-blue-hover: #0077ed;
    --indigo: #5856d6;
    --gold: #d4af37;
    --gold-text: #b8860b;
}

.stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg);
    background-image: var(--bg-gradient);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", "Helvetica Neue", sans-serif;
    -webkit-font-smoothing: antialiased;
}
[data-testid="stHeader"] {
    background: rgba(251, 251, 253, 0.72) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
}
.block-container {
    padding-top: 2.2rem;
    max-width: 1140px;
}

/* 侧边栏：毛玻璃轻质感 */
[data-testid="stSidebar"] {
    background: var(--bg-panel);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: var(--text);
}

/* 机会卡片容器：Apple 微边界 + 弥散投影 + 悬浮微动效 */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--border) !important;
    border-radius: 18px !important;
    background: var(--bg-panel) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    box-shadow: var(--shadow-card) !important;
    padding: 1rem 1.15rem !important;
    transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                box-shadow 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                border-color 0.28s ease !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover) !important;
    border-color: var(--border-hover) !important;
}

/* 顶部数据指标卡 */
[data-testid="stMetric"] {
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 0.75rem 1rem;
    background: var(--bg-panel);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    box-shadow: var(--shadow-card);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
}
[data-testid="stMetricValue"] {
    color: var(--text);
    font-size: 1.65rem;
    font-weight: 700;
    letter-spacing: -0.02em;
}
[data-testid="stMetricLabel"] {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 500;
}

/* 标题与正文排版 */
h1, h2, h3,
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3 {
    color: var(--text) !important;
    letter-spacing: -0.025em;
    font-weight: 700;
}
.stMarkdown p, label, [data-testid="stCaptionContainer"] p,
[data-testid="stSpinner"], [data-testid="stWidgetLabel"] {
    color: var(--text);
}

/* 科技感胶囊徽标（Badges） */
.badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.16rem 0.68rem;
    font-size: 0.76rem;
    font-weight: 600;
    color: var(--text);
    background: var(--bg-subtle);
    white-space: nowrap;
    line-height: 1.45;
    letter-spacing: -0.01em;
    transition: all 0.2s ease;
}
.badge-match-high {
    background: linear-gradient(135deg, #0071e3 0%, #42a5f5 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    box-shadow: 0 3px 12px rgba(0, 113, 227, 0.30);
}
.badge-match {
    background: rgba(0, 113, 227, 0.09);
    color: var(--blue);
    border-color: rgba(0, 113, 227, 0.22);
}
.badge-priority {
    background: rgba(88, 86, 214, 0.09);
    color: var(--indigo);
    border-color: rgba(88, 86, 214, 0.20);
}
.badge-urgent {
    background: linear-gradient(135deg, #ff3b30 0%, #ff6b6b 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 3px 10px rgba(255, 59, 48, 0.28);
}
.badge-warning {
    background: linear-gradient(135deg, #ff9500 0%, #ffb340 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 3px 10px rgba(255, 149, 0, 0.24);
}
.badge-blue {
    background: var(--blue-bg);
    border-color: rgba(0, 113, 227, 0.25);
    color: var(--blue);
}
.badge-gray {
    background: rgba(134, 134, 139, 0.12);
    border-color: rgba(134, 134, 139, 0.22);
    color: var(--muted);
}
.badge-pill {
    border-radius: 999px;
    padding: 0.22rem 0.9rem;
    font-size: 0.82rem;
    font-weight: 600;
}
.badge-gold {
    background: linear-gradient(135deg, rgba(212, 175, 55, 0.14), rgba(251, 245, 227, 0.6));
    border-color: rgba(212, 175, 55, 0.55) !important;
    color: var(--gold-text) !important;
}

/* 品牌渐变字 */
.brand-brief {
    background: linear-gradient(135deg, #0071e3 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.brand-flow {
    background: linear-gradient(135deg, #1d1d1f 0%, #1e3a8a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.app-title {
    font-weight: 800;
    letter-spacing: -0.03em;
    margin-bottom: 0;
}

/* 按钮体系 */
button[data-testid="stBaseButton-primary"] {
    border: none !important;
    border-radius: 999px !important;
    background: linear-gradient(135deg, var(--btn-blue) 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
    box-shadow: 0 4px 14px rgba(0, 113, 227, 0.28) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease !important;
}
button[data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(0, 113, 227, 0.38) !important;
    filter: brightness(1.05);
}

button[data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    font-weight: 500;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.2s ease !important;
}
button[data-testid="stBaseButton-secondary"]:hover {
    background: var(--blue-bg) !important;
    border-color: var(--border-hover) !important;
    color: var(--blue) !important;
}

a[data-testid="stLinkButton"] {
    border: 1px solid var(--border) !important;
    border-radius: 999px !important;
    background: var(--bg-subtle) !important;
    color: var(--blue) !important;
    font-weight: 600;
    font-size: 0.82rem;
    transition: all 0.2s ease !important;
}
a[data-testid="stLinkButton"]:hover {
    background: var(--blue-bg) !important;
    border-color: var(--border-hover) !important;
    transform: translateY(-1px);
}

[data-testid="stTextInput"] input {
    border: 1px solid rgba(0, 0, 0, 0.10) !important;
    border-radius: 14px !important;
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    box-shadow: var(--shadow-sm) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.14) !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    background: var(--bg-panel) !important;
    box-shadow: var(--shadow-sm) !important;
}

[data-testid="stExpander"] details {
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    background: var(--bg-subtle) !important;
    margin-top: 0.35rem;
}
[data-testid="stExpander"] summary {
    color: var(--muted);
    font-size: 0.85rem;
    font-weight: 500;
}

[data-testid="stAlert"] {
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    box-shadow: var(--shadow-sm);
}

/* 侧边栏付费按钮：Apple 质感流光金边 */
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    border: 1.5px solid rgba(212, 175, 55, 0.75) !important;
    background: linear-gradient(135deg, rgba(255, 250, 235, 0.9), rgba(251, 240, 205, 0.75)) !important;
    color: #9a6f00 !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(212, 175, 55, 0.18) !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #fff8e1, #f7e6b5) !important;
    box-shadow: 0 6px 18px rgba(212, 175, 55, 0.28) !important;
}

/* 升级弹窗卡片样式 */
.pricing-card {
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.35rem 1.2rem;
    min-height: 290px;
    background: var(--bg-panel);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: var(--shadow-card);
    position: relative;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease;
}
.pricing-card:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-hover);
}
.pricing-card-pro {
    border: 1.5px solid rgba(0, 113, 227, 0.45);
    background: linear-gradient(180deg, rgba(0, 113, 227, 0.05) 0%, var(--bg-panel) 100%);
    box-shadow: 0 12px 32px -4px rgba(0, 113, 227, 0.14), 0 0 0 1px rgba(212, 175, 55, 0.35);
}
.pricing-badge-top {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 0.15rem 0.65rem;
    border-radius: 999px;
    margin-bottom: 0.55rem;
}

/* Apple 风格分段控制器 (Segmented Switcher) */
.tier-switcher-box {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.3rem 0.35rem;
    background: var(--bg-subtle);
    border: 1px solid var(--border);
    border-radius: 999px;
    box-shadow: var(--shadow-sm);
}
</style>
"""

# 深色模式
_DARK_CSS = """
<style>
:root {
    --bg: #000000;
    --bg-gradient: radial-gradient(1200px 500px at 50% -120px, rgba(41, 151, 255, 0.14), transparent 70%);
    --bg-panel: rgba(28, 28, 30, 0.78);
    --bg-subtle: rgba(44, 44, 46, 0.65);
    --text: #f5f5f7;
    --muted: #86868b;
    --line: rgba(255, 255, 255, 0.08);
    --border: rgba(255, 255, 255, 0.09);
    --border-hover: rgba(41, 151, 255, 0.40);
    --shadow-sm: 0 2px 10px rgba(0, 0, 0, 0.4);
    --shadow-card: 0 8px 28px -4px rgba(0, 0, 0, 0.55);
    --shadow-hover: 0 14px 36px -4px rgba(0, 0, 0, 0.75);
    --blue: #2997ff;
    --blue-bg: rgba(41, 151, 255, 0.15);
    --btn-blue: #0071e3;
    --btn-blue-hover: #2997ff;
    --indigo: #7d7aff;
    --gold: #ffd60a;
    --gold-text: #ffd60a;
}
[data-testid="stHeader"] {
    background: rgba(0, 0, 0, 0.72) !important;
}
.brand-flow {
    background: linear-gradient(135deg, #f5f5f7 0%, #93c5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.stApp {
    --text-color: #f5f5f7;
    --background-color: #000000;
    --secondary-background-color: #1c1c1e;
    --primary-color: #2997ff;
}
[data-testid="stTextInput"] input {
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    border: 1.5px solid rgba(255, 214, 10, 0.55) !important;
    background: linear-gradient(135deg, rgba(255, 214, 10, 0.16), rgba(212, 175, 55, 0.08)) !important;
    color: #ffd60a !important;
}
.badge-gold {
    background: rgba(255, 214, 10, 0.12);
    border-color: rgba(255, 214, 10, 0.45) !important;
    color: #ffd60a !important;
}
[data-testid="stAlert"] {
    background-color: rgba(28, 36, 51, 0.82) !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] span {
    color: #f5f5f7 !important;
}
</style>
"""

st.markdown(_BASE_CSS, unsafe_allow_html=True)


def _badge(label: str, value, kind: str = "default") -> str:
    """科技感胶囊徽标。"""
    cls_map = {
        "default": "badge",
        "blue": "badge badge-blue",
        "gray": "badge badge-gray",
        "match-high": "badge badge-match-high",
        "match": "badge badge-match",
        "priority": "badge badge-priority",
        "urgent": "badge badge-urgent",
        "warning": "badge badge-warning",
    }
    cls = cls_map.get(kind, "badge")
    return f'<span class="{cls}">{label} {value}</span>'


def _execute_search(query: str, tier: str, spinner_text: str = "正在理解需求并筛选机会...") -> bool:
    """执行检索并同步更新会话状态；成功返回 True。"""
    st.session_state.pop("search_error", None)
    st.session_state.pop("viewing_history", None)
    clean_query = query.strip()
    if not clean_query:
        st.session_state.pop("search_result", None)
        st.session_state.search_error = "请输入检索需求。"
        return False
    try:
        with st.spinner(spinner_text):
            fresh_result = run_brief_flow(clean_query, tier=tier)
            st.session_state.search_result = fresh_result
            st.session_state.retrieval_mode = os.environ.get("BRIEFFLOW_RETRIEVAL_MODE", "mock").strip().lower()
            st.session_state.searched_query = clean_query
        st.session_state.history.insert(
            0,
            {
                "query": clean_query,
                "time": datetime.now().strftime("%m-%d %H:%M"),
                "result": fresh_result,
            },
        )
        st.session_state.history = st.session_state.history[:10]
        return True
    except Exception:
        st.session_state.search_error = "检索失败，未生成结果。请检查后端配置后重试。"
        return False


def switch_tier_and_resync(new_tier: str):
    """切换会员等级并立即触发检索同步与界面刷新。"""
    if st.session_state.get("tier") == new_tier and st.session_state.get("search_result"):
        # 即使等级相同，如果尚未执行过检索则无需动作
        return
    st.session_state.tier = new_tier
    st.session_state.show_count_select = 50 if new_tier == "free" else 20
    active_query = (
        st.session_state.get("searched_query")
        or st.session_state.get("query_input")
        or ""
    ).strip()
    if st.session_state.get("search_result") is not None and active_query:
        _execute_search(
            active_query,
            tier=new_tier,
            spinner_text=f"正在按 {TIERS[new_tier]['name']} 权限重新匹配并更新筛选...",
        )
    st.rerun()


_PLAN_FEATURES = {
    "free": [
        "开放 2 个搜索条件与基础模块",
        "按「类型」单维度快速匹配",
        "单次展示最多 5 条精选结果",
        "保留最近 5 条检索历史",
    ],
    "plus": [
        "开放 4 个搜索条件与进阶模块",
        "类型 + 地点 + 专业 + 年级多维匹配",
        "单次展示最多 20 条高优结果",
        "保留最近 50 条检索历史",
    ],
    "pro": [
        "开放全部 6 大模块与不限条件",
        "全维度深度匹配 + 排除条件强过滤",
        "不限结果条数 + 完整多源数据池",
        "不限历史 + Qwen/LLM 增强简报摘要",
    ],
}

_PLAN_TAGLINES = {
    "free": ("入门体验", "background:var(--bg-subtle);color:var(--muted);"),
    "plus": ("进阶首选", "background:var(--blue-bg);color:var(--blue);"),
    "pro": ("旗舰推荐 · FULL ACCESS", "background:linear-gradient(135deg,#0071e3,#42a5f5);color:#ffffff;"),
}


@st.dialog("升级 BriefFlow 会员", width="large")
def show_upgrade_dialog():
    """Apple / ChatGPT 风格三列对比订阅弹窗。"""
    current = st.session_state.get("tier", "free")
    st.caption("内测体验期：所有付费方案限时 ¥0 免费解锁，切换后立即自动刷新当前检索结果。")
    cols = st.columns(3)
    for col, key in zip(cols, ("free", "plus", "pro")):
        name = TIERS[key]["name"]
        price = TIERS[key]["price"]
        features = _PLAN_FEATURES[key]
        tag_text, tag_style = _PLAN_TAGLINES[key]
        highlighted = key == "pro"
        card_cls = "pricing-card pricing-card-pro" if highlighted else "pricing-card"
        title_color = "var(--blue)" if highlighted else "var(--text)"
        if price == 0:
            price_html = (
                '<span style="font-weight:800;font-size:1.85rem;letter-spacing:-0.03em;color:var(--text);">¥0</span>'
                '<span style="font-size:0.82rem;color:var(--muted);margin-left:4px;">/ 永久基础版</span>'
            )
        else:
            price_html = (
                f'<s style="color:var(--muted);font-size:0.95rem;">¥{price}/月</s> '
                '<span style="font-weight:800;font-size:1.85rem;letter-spacing:-0.03em;color:var(--text);">¥0</span>'
                '<span style="font-size:0.78rem;color:var(--blue);font-weight:600;margin-left:4px;">内测限免</span>'
            )
        features_html = "".join(
            f'<div style="font-size:0.86rem;color:var(--text);margin:0.48rem 0;display:flex;align-items:flex-start;gap:0.4rem;">'
            f'<span style="color:var(--blue);font-weight:700;">✓</span><span>{f}</span></div>'
            for f in features
        )
        with col:
            st.markdown(
                f'<div class="{card_cls}">'
                f'<span class="pricing-badge-top" style="{tag_style}">{tag_text}</span>'
                f'<div style="font-weight:800;font-size:1.35rem;color:{title_color};letter-spacing:-0.02em;">{name}</div>'
                f'<div style="margin:0.55rem 0 0.9rem;padding-bottom:0.75rem;border-bottom:1px solid var(--line);">{price_html}</div>'
                f"{features_html}"
                f"</div>",
                unsafe_allow_html=True,
            )
            if key == current:
                st.button("当前方案", key=f"cur_{key}", disabled=True, use_container_width=True)
            elif st.button("立即解锁", key=f"buy_{key}", type="primary", use_container_width=True):
                switch_tier_and_resync(key)


# 初始态 hero 标题与样式
_HERO_TITLE = """
<div style="text-align:center;margin-top:2.8rem;margin-bottom:0.3rem;">
    <span class="badge badge-blue badge-pill" style="margin-bottom:0.8rem;">AI Opportunity Intelligence · 个人机会简报系统</span>
</div>
<h1 class="hero-title"><span class="brand-brief">Brief</span><span class="brand-flow">Flow</span></h1>
"""

_HERO_CSS = """
<style>
.hero-title {
    text-align: center;
    font-size: 5.2rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    margin: 0.2rem 0 0.5rem;
    line-height: 1.08;
}
.block-container { max-width: 780px; }
[data-testid="stTextInput"] { max-width: 600px; margin-left: auto; margin-right: auto; }
[data-testid="stTextInput"] input { font-size: 1.02rem; padding: 0.78rem 1.05rem; }
button[data-testid="stBaseButton-primary"] {
    font-size: 1.02rem;
    padding: 0.58rem 2.1rem;
    display: block;
    margin-left: auto;
    margin-right: auto;
}
</style>
"""

result = st.session_state.get("search_result")
if result is None:
    st.markdown(_HERO_CSS, unsafe_allow_html=True)
    st.markdown(_HERO_TITLE, unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align:center;color:var(--muted);font-size:1.05rem;margin-bottom:1.6rem;">'
        "你的个人机会简报 · 理解需求，筛选机会，说明推荐理由</p>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<h1 class="app-title"><span class="brand-brief">Brief</span><span class="brand-flow">Flow</span></h1>',
        unsafe_allow_html=True,
    )
    st.caption("你的个人机会简报 · 理解需求，筛选机会，说明推荐理由")

user_query = st.text_input(
    "请输入你的需求：",
    key="query_input",
    value="我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。",
)
if st.button("开始检索", type="primary"):
    current_tier = st.session_state.get("tier", "free")
    if _execute_search(user_query, tier=current_tier):
        if current_tier == "free" and not st.session_state.get("upgrade_prompted"):
            st.session_state.upgrade_prompted = True
            st.session_state.show_upgrade = True
        st.rerun()

# 首次 free 检索后自动弹出付费弹窗（仅一次）
if st.session_state.get("show_upgrade"):
    st.session_state.show_upgrade = False
    show_upgrade_dialog()

result = st.session_state.get("search_result")
with st.sidebar:
    st.header("BriefFlow")
    if st.button("付费选项", key="pricing_btn", type="primary"):
        show_upgrade_dialog()
    tier_name = TIERS[st.session_state.get("tier", "free")]["name"]
    st.markdown(
        f'<span class="badge badge-gold badge-pill">当前方案：{tier_name}</span>',
        unsafe_allow_html=True,
    )
    st.subheader("Agent Mode")
    if result:
        enhanced = result.get("summary_mode") == "llm"
        qwen_enhanced = (
            enhanced
            and result.get("summary_provider") == "qwen"
            and result.get("input_mode") == "llm"
            and result.get("input_provider") == "qwen"
        )
        if enhanced:
            status_label, status_kind = ("Qwen Enhanced" if qwen_enhanced else "LLM Enhanced"), "blue"
        else:
            status_label, status_kind = "Rule-based Fallback", "gray"
        st.markdown(
            f'<span class="badge badge-{status_kind} badge-pill">{status_label}</span>',
            unsafe_allow_html=True,
        )
        st.caption("AI-generated Brief" if enhanced else "Rule-based Brief")
        st.caption(
            "本次摘要使用 LLM 选择经核实的事实措辞。"
            if enhanced
            else "本次摘要由规则生成；未使用 LLM 摘要，或 LLM 调用未通过校验。"
        )
        if enhanced and result.get("input_mode") != "llm":
            st.caption("Input Agent 使用规则回退；摘要阶段使用 LLM。")
    else:
        st.write("尚未生成 Brief")
        st.caption("检索后显示本次实际摘要模式。")
    st.divider()
    st.subheader("历史")
    if st.session_state.get("history"):
        for i, entry in enumerate(st.session_state.history):
            label = f"{entry['time']}  {entry['query']}"
            if len(label) > 26:
                label = label[:26] + "…"
            if st.button(label, key=f"hist_{i}"):
                st.session_state.search_result = entry["result"]
                st.session_state.searched_query = entry["query"]
                st.session_state.viewing_history = f"{entry['query']}（{entry['time']}）"
        if st.button("清空历史", key="clear_history"):
            st.session_state.history = []
            st.session_state.pop("viewing_history", None)
            st.rerun()
    else:
        st.caption("暂无历史记录。")
    st.divider()
    with st.expander("设置"):
        st.toggle("深色模式", key="dark_mode")
    with st.expander("关于"):
        st.caption("BriefFlow —— 基于 AI Agent 的个性化情报简报服务。")
        st.caption("自动完成信息获取、筛选、匹配、摘要与持续推送。")
    st.info("修改需求后重新检索，即可生成新的机会简报。")
    st.caption("演示数据会明确标注。申请资格与截止日期请以官方来源为准。")

if st.session_state.get("dark_mode"):
    st.markdown(_DARK_CSS, unsafe_allow_html=True)

result = st.session_state.get("search_result")

if st.session_state.get("search_error"):
    st.error(st.session_state.search_error)

if result is not None:
    if st.session_state.get("viewing_history"):
        st.info(f"正在查看历史记录：{st.session_state.viewing_history}")
    elif st.session_state.get("searched_query", user_query) != user_query:
        st.info("当前仍显示上一次检索结果；点击开始检索以更新。")
    items = result.get("recommended_items") or []
    raw_stats = result.get("result_stats") or {}
    try:
        as_of = date.fromisoformat(raw_stats.get("as_of", ""))
    except (ValueError, TypeError):
        as_of = None
    stats = describe_items(
        items,
        as_of=as_of,
        requested_mode=st.session_state.get("retrieval_mode", "mock"),
    )
    retrieval = result.get("retrieval") or {}
    source_mode = retrieval.get("data_source_mode") or stats["data_source_mode"]
    mock_count = retrieval.get("mock_count", stats["mock_count"])
    fallback = retrieval.get("fallback", stats["retrieval_fallback"])
    today = date.fromisoformat(stats["as_of"])
    if mock_count or source_mode == "Mock Data":
        st.warning("Demo / Mock Data：模拟机会，非真实招聘或报名信息。")
    if fallback:
        st.warning("实时数据获取失败或无可用数据，本次使用 Demo Mock Data。")
    if source_mode == "Web Data":
        st.caption("真实来源记录不等于已确认可申请的机会；申请资格及截止日期请以官方来源为准。")
    st.subheader("AI Brief")
    st.caption("AI-generated Brief" if result.get("summary_mode") == "llm" else "Rule-based Brief")
    st.info(result.get("summary") or "本次未生成摘要，请查看下方结果。")
    st.caption(f"{stats['high_match']} 条高匹配机会 · {stats['urgent_deadline']} 条 7 天内截止")

    # ================= 核心改进：即时会员方案切换器 + 权限门控呈现 =================
    current_tier = st.session_state.get("tier", "free")
    pref_header_col, switcher_col = st.columns([1.5, 2.5])
    with pref_header_col:
        st.subheader("已理解的偏好")
    with switcher_col:
        # 页面原生常驻分段切换器：无需弹窗，点选立即触发重新筛选与刷新
        st.write("")
        st.caption("会员权限即时体验（点击直接生效）：")
        tier_cols = st.columns(3)
        for t_col, t_key, t_label in zip(
            tier_cols,
            ("free", "plus", "pro"),
            ("Free (限2项)", "Plus (限4项)", "Pro (全部)"),
        ):
            is_active = t_key == current_tier
            btn_type = "primary" if is_active else "secondary"
            btn_text = f"● {t_label}" if is_active else t_label
            if t_col.button(btn_text, key=f"quick_tier_{t_key}", type=btn_type, use_container_width=True):
                if not is_active:
                    switch_tier_and_resync(t_key)

    st.caption("已理解的筛选偏好 · 依据当前会员等级开放权限参与下游匹配：")

    preference = result.get("preference") or {}
    # 定义规范偏好字段与其重要度顺序（类型、地点、偏好、排除、专业、年级、时间）
    candidate_fields = [
        ("类型", "categories"),
        ("地点", "locations"),
        ("偏好", "keywords"),
        ("排除", "exclude_keywords"),
        ("专业", "disciplines"),
        ("年级", "grades"),
        ("时间", "time_pref"),
    ]

    # 提取实际有值的字段
    active_field_list = []
    for label, field in candidate_fields:
        vals = preference.get(field) or []
        if isinstance(vals, str):
            vals = [vals]
        if vals:
            active_field_list.append((label, field, vals))

    # 根据方案规定允许参与的搜索条件数量：Free 2项，Plus 4项，Pro 全部
    allowed_count = 2 if current_tier == "free" else (4 if current_tier == "plus" else 999)

    # 渲染两列偏好卡片，精准标注「参与检索」或「受限未启用」
    left, right = st.columns(2)
    dropped_count = 0
    dropped_labels = []

    for idx, (label, field, values) in enumerate(active_field_list):
        target_col = left if idx % 2 == 0 else right
        val_text = " · ".join(str(v) for v in values)
        is_allowed = idx < allowed_count

        if is_allowed:
            status_badge = _badge("参与检索", "", "blue")
            target_col.markdown(
                f"{label}：**{val_text}** {status_badge}",
                unsafe_allow_html=True,
            )
        else:
            dropped_count += 1
            dropped_labels.append(label)
            status_badge = _badge("受限未启用", "", "gray")
            target_col.markdown(
                f"<span style='color:var(--muted);'>{label}：<strike>{val_text}</strike></span> {status_badge}",
                unsafe_allow_html=True,
            )

    # 动态提示横幅：视觉上立竿见影呈现权限差异
    if dropped_count > 0:
        st.warning(
            f"当前为 **{TIERS[current_tier]['name']}**（限前 {allowed_count} 项条件），"
            f"以下维度已被权限门控忽略：{'、'.join(dropped_labels)}。"
            f"升级至 Plus 或 Pro 可立即解锁全维度精确匹配与排除过滤。"
        )
    elif current_tier == "pro":
        st.success("✦ 已开启 Pro 旗舰特权：全维度条件匹配与排除过滤已全部生效，获得最精准推荐。")

    st.divider()
    a, b, c, d = st.columns(4)
    a.metric("Total Opportunities", stats["total"])
    b.metric("High Match", stats["high_match"], help="已有 Match Score ≥ 80 的条目数量，不代表录取概率。")
    c.metric("Urgent Deadline", stats["urgent_deadline"], help="从今天起 7 天内截止，包含今天；不含已过期或日期未知条目。")
    d.metric("Data Source Mode", source_mode)
    st.caption(f"统计日期：{stats['as_of']}（北京时间） · 高匹配 ≥ 80 · 临近截止 0–7 天（含今天）")
    st.subheader("推荐机会")
    st.caption("Match Score：与你需求的匹配程度。Priority Score：结合匹配度、时效和截止时间后的推荐优先级。")
    if not items:
        if source_mode == "Web Data" and retrieval.get("retrieved_count", 0):
            st.caption(
                f"已取得 {retrieval['retrieved_count']} 条真实来源记录，本次筛选后为 0 条。地点未注明等条件可能影响匹配；未改用 Mock 数据。"
            )
        st.info("暂无匹配机会。可以减少地点限制或调整机会类型后重试。")
    else:
        # 展示条数根据会员等级自适应：Free 不限条数（默认展示更多），Plus/Pro 默认 20 条
        default_idx = 3 if current_tier == "free" else 2
        show_count = st.selectbox("展示数量", [5, 10, 20, 50], index=default_idx, key="show_count_select")
        st.caption(f"当前展示 {min(show_count, len(items))} / {len(items)} 条 · 保持原始推荐顺序")
        for index, item in enumerate(items[:show_count], 1):
            title = item.get("title") or "未命名机会"
            match_score = item.get("match_score", "未提供")
            priority_score = item.get("priority_score", "未提供")
            days = deadline_days(item, today)
            deadline = item.get("deadline") or "未注明"
            if days is not None and days < 0:
                ddl_short, ddl_kind = "已截止", "gray"
            elif days is not None and days <= 3:
                ddl_short, ddl_kind = ("今天截止" if days == 0 else f"{days}天后截止"), "urgent"
            elif days is not None and days <= 7:
                ddl_short, ddl_kind = f"{days}天后截止", "warning"
            else:
                ddl_short, ddl_kind = deadline, "default"

            match_kind = "match-high" if is_high_match(item) else "match"

            source_url = item.get("source_url") or item.get("link")
            link_text, link_url = None, None
            if isinstance(source_url, str):
                try:
                    url = urlsplit(source_url)
                    if url.scheme in ("http", "https") and url.hostname and not url.username and not url.password:
                        link_url = source_url
                        link_text = "示例来源" if "mock" in str(item.get("source", "")).lower() else "原始来源"
                except ValueError:
                    pass

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3.4, 1, 1, 1.5, 0.9])
                c1.markdown(f"**{title}**")
                c2.markdown(_badge("匹配", match_score, match_kind), unsafe_allow_html=True)
                c3.markdown(_badge("优先", priority_score, "priority"), unsafe_allow_html=True)
                c4.markdown(_badge("截止", ddl_short, ddl_kind), unsafe_allow_html=True)
                if link_url:
                    c5.link_button(link_text, link_url)
                else:
                    c5.caption("—")
                with st.expander("详情", expanded=False):
                    organization = item.get("organization") or item.get("company") or "机构未注明"
                    st.write(organization)
                    st.caption(f"{item.get('location') or '未注明'} · {item.get('category') or '未分类'}")
                    if is_high_match(item):
                        st.caption("高匹配 · Match Score ≥ 80")
                    st.write("**为什么推荐给你**")
                    reasons = item.get("why_recommended") or []
                    if isinstance(reasons, str):
                        reasons = [reasons]
                    for reason in reasons[:3]:
                        st.write("- " + re.sub(r"\+\d+(?:\.\d+)?$", "", str(reason)))
                    if not reasons:
                        st.caption("暂无详细推荐理由。")
                    if len(reasons) > 3:
                        with st.expander("更多推荐理由"):
                            for reason in reasons[3:]:
                                st.write("- " + str(reason))
                    source = item.get("source") or "未注明"
                    st.caption(f"来源：{source}")
                    st.caption(f"截止日期：{deadline}")