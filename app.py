"""Streamlit demo calls the Python Router directly; no FastAPI server required."""
import os
import re
from datetime import date, datetime
from urllib.parse import urlsplit

import streamlit as st
from backend.router.service import run_brief_flow
from backend.output_agent.presentation import describe_items, is_high_match, deadline_days

st.set_page_config(page_title="BriefFlow 个人情报站", layout="wide")

# 会话状态初始化
st.session_state.setdefault("history", [])
st.session_state.setdefault("dark_mode", False)

# 基础样式：所有颜色走 CSS 变量，深浅色切换只需改变量
_BASE_CSS = """
<style>
:root {
    --bg: #ffffff;
    --bg-panel: #ffffff;
    --text: #111827;
    --muted: #6b7280;
    --line: #e5e7eb;
    --border: #111827;
    --blue: #2563eb;
    --blue-bg: #eff6ff;
    --btn-blue: #2563eb;
    --btn-blue-hover: #1d4ed8;
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background: var(--bg);
}
.block-container { padding-top: 2rem; max-width: 1180px; }

[data-testid="stSidebar"] {
    background: var(--bg);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: var(--text);
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1.5px solid var(--border) !important;
    border-radius: 14px;
    background: var(--bg-panel);
}

[data-testid="stMetric"] {
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 0.5rem 0.85rem;
    background: var(--bg-panel);
}
[data-testid="stMetricValue"] { color: var(--text); font-size: 1.5rem; }
[data-testid="stMetricLabel"] { color: var(--muted); }

h1, h2, h3,
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3 {
    color: var(--text) !important;
    letter-spacing: -0.02em;
}
.stMarkdown p, label, [data-testid="stCaptionContainer"] p,
[data-testid="stSpinner"], [data-testid="stWidgetLabel"] { color: var(--text); }

.badge {
    display: inline-block;
    border: 1.5px solid var(--border);
    border-radius: 8px;
    padding: 0.05rem 0.5rem;
    font-size: 0.78rem;
    color: var(--text);
    white-space: nowrap;
    line-height: 1.5;
}
.badge-blue { border-color: var(--blue); color: var(--blue); }
.badge-gray { border-color: var(--muted); color: var(--muted); }
.badge-pill { border-radius: 999px; padding: 0.15rem 0.85rem; font-size: 0.85rem; font-weight: 600; }
.brand-brief { color: #38bdf8; }
.brand-flow { color: #1e3a8a; }
.app-title { font-style: italic; margin-bottom: 0; }

button[data-testid="stBaseButton-primary"] {
    border: 1.5px solid var(--btn-blue) !important;
    border-radius: 10px !important;
    background: var(--btn-blue) !important;
    color: #ffffff !important;
    font-weight: 700;
}
button[data-testid="stBaseButton-primary"]:hover { background: var(--btn-blue-hover) !important; }

button[data-testid="stBaseButton-secondary"] {
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    font-weight: 500;
}
button[data-testid="stBaseButton-secondary"]:hover { background: var(--blue-bg) !important; }

a[data-testid="stLinkButton"] {
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    background: var(--bg-panel) !important;
    color: var(--text) !important;
    font-weight: 600;
}

[data-testid="stTextInput"] input {
    border: 1.5px solid var(--muted) !important;
    border-radius: 10px !important;
    color: var(--muted) !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
}

[data-testid="stExpander"] details {
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--bg-panel);
}
[data-testid="stExpander"] summary { color: var(--text); }
</style>
"""

# 深色模式：覆盖变量 + 通知框深色化
_DARK_CSS = """
<style>
:root {
    --bg: #0f1115;
    --bg-panel: #16181d;
    --text: #e5e7eb;
    --muted: #9ca3af;
    --line: #2a2e37;
    --border: #4b5563;
    --blue: #60a5fa;
    --blue-bg: #1e2a45;
    --btn-blue: #3b82f6;
    --btn-blue-hover: #2563eb;
}
.brand-flow { color: #93c5fd; }
/* 覆盖 Streamlit 自带主题变量，让未显式指定的默认文字/背景也跟随深色 */
.stApp {
    --text-color: #e5e7eb;
    --background-color: #0f1115;
    --secondary-background-color: #16181d;
    --primary-color: #60a5fa;
}
[data-testid="stAlert"] {
    background-color: #1c2433 !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] span {
    color: #e5e7eb !important;
}
</style>
"""

st.markdown(_BASE_CSS, unsafe_allow_html=True)


def _badge(label: str, value, kind: str = "default") -> str:
    """描边小徽标；kind: default / blue / gray，随深浅色主题自动适配。"""
    cls = {"default": "badge", "blue": "badge badge-blue", "gray": "badge badge-gray"}[kind]
    return f'<span class="{cls}">{label} {value}</span>'


# 初始态 hero 标题与样式
_HERO_TITLE = """
<h1 class="hero-title"><span class="brand-brief">Brief</span><span class="brand-flow">Flow</span></h1>
"""

_HERO_CSS = """
<style>
.hero-title {
    font-style: italic;
    text-align: center;
    font-size: 6rem;
    font-weight: 900;
    letter-spacing: -0.02em;
    margin: 3rem 0 0.5rem;
}
.block-container { max-width: 760px; }
[data-testid="stTextInput"] { max-width: 560px; margin-left: auto; margin-right: auto; }
[data-testid="stTextInput"] input { font-size: 1.05rem; padding: 0.7rem 0.9rem; }
[data-testid="stBaseButton-primary"] { font-size: 1.05rem; padding: 0.55rem 1.8rem; display: block; margin-left: auto; margin-right: auto; }
</style>
"""

# 初始态（尚未检索）居中大标题；检索后恢复常规布局
result = st.session_state.get("search_result")
if result is None:
    st.markdown(_HERO_CSS, unsafe_allow_html=True)
    st.markdown(_HERO_TITLE, unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align:center;color:var(--muted);">你的个人机会简报 · 理解需求，筛选机会，说明推荐理由</p>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<h1 class="app-title"><span class="brand-brief">Brief</span><span class="brand-flow">Flow</span></h1>', unsafe_allow_html=True)
    st.caption("你的个人机会简报 · 理解需求，筛选机会，说明推荐理由")

user_query = st.text_input(
    "请输入你的需求：",
    key="query_input",
    value="我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。",
)
if st.button("开始检索", type="primary"):
    st.session_state.pop("search_result", None)
    st.session_state.pop("search_error", None)
    st.session_state.pop("viewing_history", None)
    if not user_query.strip():
        st.session_state.search_error = "请输入检索需求。"
    else:
        try:
            with st.spinner("正在理解需求并筛选机会..."):
                fresh_result = run_brief_flow(user_query)
                st.session_state.search_result = fresh_result
                st.session_state.retrieval_mode = os.environ.get("BRIEFFLOW_RETRIEVAL_MODE", "mock").strip().lower()
                st.session_state.searched_query = user_query
            # 记录历史（回看用，上限 10 条）
            st.session_state.history.insert(0, {
                "query": user_query,
                "time": datetime.now().strftime("%m-%d %H:%M"),
                "result": fresh_result,
            })
            st.session_state.history = st.session_state.history[:10]
        except Exception:
            st.session_state.search_error = "检索失败，未生成结果。请检查后端配置后重试。"
        else:
            # 检索成功后重跑，让标题从 hero 切换为常规布局
            st.rerun()

result = st.session_state.get("search_result")
with st.sidebar:
    st.header("BriefFlow")
    st.subheader("Agent Mode")
    if result:
        enhanced = result.get("summary_mode") == "llm"
        qwen_enhanced = (enhanced and result.get('summary_provider') == 'qwen'
                         and result.get('input_mode') == 'llm' and result.get('input_provider') == 'qwen')
        if enhanced:
            status_label, status_kind = ("Qwen Enhanced" if qwen_enhanced else "LLM Enhanced"), "blue"
        else:
            status_label, status_kind = "Rule-based Fallback", "gray"
        st.markdown(f'<span class="badge badge-{status_kind} badge-pill">{status_label}</span>',
                    unsafe_allow_html=True)
        st.caption("AI-generated Brief" if enhanced else "Rule-based Brief")
        st.caption("本次摘要使用 LLM 选择经核实的事实措辞。" if enhanced else
                   "本次摘要由规则生成；未使用 LLM 摘要，或 LLM 调用未通过校验。")
        if enhanced and result.get('input_mode') != 'llm':
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

# 深色模式覆盖（晚于基础样式注入，确保变量生效）
if st.session_state.get("dark_mode"):
    st.markdown(_DARK_CSS, unsafe_allow_html=True)

# 历史点击会更新 search_result，重新读取以立即渲染主区域
result = st.session_state.get("search_result")

if st.session_state.get("search_error"):
    st.error(st.session_state.search_error)

if result is not None:
    if st.session_state.get("viewing_history"):
        st.info(f"正在查看历史记录：{st.session_state.viewing_history}")
    elif st.session_state.get("searched_query", user_query) != user_query:
        st.info("当前仍显示上一次检索结果；点击开始检索以更新。")
    items = result.get("recommended_items") or []
    # Recompute all counters from actual items, not optional/model-supplied numbers.
    raw_stats = result.get("result_stats") or {}
    try:
        as_of = date.fromisoformat(raw_stats.get("as_of", ""))
    except (ValueError, TypeError):
        as_of = None
    stats = describe_items(items, as_of=as_of,
                           requested_mode=st.session_state.get("retrieval_mode", "mock"))
    retrieval = result.get('retrieval') or {}
    source_mode = retrieval.get('data_source_mode') or stats['data_source_mode']
    mock_count = retrieval.get('mock_count', stats['mock_count'])
    fallback = retrieval.get('fallback', stats['retrieval_fallback'])
    today = date.fromisoformat(stats["as_of"])
    if mock_count or source_mode == "Mock Data":
        st.warning("Demo / Mock Data：模拟机会，非真实招聘或报名信息。")
    if fallback:
        st.warning("实时数据获取失败或无可用数据，本次使用 Demo Mock Data。")
    if source_mode == 'Web Data':
        st.caption("真实来源记录不等于已确认可申请的机会；申请资格及截止日期请以官方来源为准。")
    st.subheader("AI Brief")
    st.caption("AI-generated Brief" if result.get("summary_mode") == "llm" else "Rule-based Brief")
    st.info(result.get("summary") or "本次未生成摘要，请查看下方结果。")
    # These highlights are also computed, so legacy/missing optional fields are safe.
    st.caption(f"{stats['high_match']} 条高匹配机会 · {stats['urgent_deadline']} 条 7 天内截止")

    st.subheader("已理解的偏好")
    st.caption("已理解的筛选偏好 · 仅下列偏好参与筛选；本科资格等申请条件请查看来源核实。")
    preference = result.get("preference") or {}
    left, right = st.columns(2)
    for column, label, field in (
        (left, "地点", "locations"), (right, "类型", "categories"),
        (left, "偏好", "keywords"), (right, "排除", "exclude_keywords"),
    ):
        values = preference.get(field) or []
        if isinstance(values, str):
            values = [values]
        column.write(f"{label}：{' · '.join(str(value) for value in values) or '未指定'}")

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
        if source_mode == 'Web Data' and retrieval.get('retrieved_count', 0):
            st.caption(f"已取得 {retrieval['retrieved_count']} 条真实来源记录，本次筛选后为 0 条。地点未注明等条件可能影响匹配；未改用 Mock 数据。")
        st.info("暂无匹配机会。可以减少地点限制或调整机会类型后重试。")
    else:
        show_count = st.selectbox("展示数量", [5, 10, 20], index=0)
        st.caption(f"当前展示 {min(show_count, len(items))} / {len(items)} 条 · 保持原始推荐顺序")
        for index, item in enumerate(items[:show_count], 1):
            title = item.get("title") or "未命名机会"
            match_score = item.get("match_score", "未提供")
            priority_score = item.get("priority_score", "未提供")
            days = deadline_days(item, today)
            deadline = item.get("deadline") or "未注明"
            if days is not None and days < 0:
                ddl_short, ddl_kind = "已截止", "gray"
            elif days is not None and days <= 7:
                ddl_short, ddl_kind = ("今天截止" if days == 0 else f"{days}天后截止"), "blue"
            else:
                ddl_short, ddl_kind = deadline, "default"

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
                # 折叠后仍可见的常驻行：title + 两个分数 + ddl + 链接
                c1, c2, c3, c4, c5 = st.columns([3.4, 1, 1, 1.5, 0.9])
                c1.markdown(f"**{title}**")
                c2.markdown(_badge("匹配", match_score), unsafe_allow_html=True)
                c3.markdown(_badge("优先", priority_score), unsafe_allow_html=True)
                c4.markdown(_badge("截止", ddl_short, ddl_kind), unsafe_allow_html=True)
                if link_url:
                    c5.link_button(link_text, link_url)
                else:
                    c5.caption("—")
                # 可折叠详情
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
                        # Remove only the trailing arithmetic contribution for readable bullets.
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

