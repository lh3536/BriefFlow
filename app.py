"""Streamlit demo calls the Python Router directly; no FastAPI server required."""
import os
import re
from datetime import date
from urllib.parse import urlsplit

import streamlit as st
from backend.router.service import run_brief_flow
from backend.output_agent.presentation import describe_items, is_high_match, deadline_days

st.set_page_config(page_title="BriefFlow 个人情报站", page_icon="💼", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 1180px;}
[data-testid="stSidebar"] {background: #f1f5f8;}
[data-testid="stMetricValue"] {font-size: 1.65rem;}
[data-testid="stMetricLabel"] {color: #536777;}
h1, h2, h3 {letter-spacing: -.025em;}
</style>
""", unsafe_allow_html=True)
st.title("🔍 BriefFlow")
st.caption("你的个人机会简报 · 理解需求，筛选机会，说明推荐理由")
user_query = st.text_input(
    "请输入你的需求：",
    value="我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。",
)
if st.button("🚀 开始检索", type="primary"):
    st.session_state.pop("search_result", None)
    st.session_state.pop("search_error", None)
    if not user_query.strip():
        st.session_state.search_error = "请输入检索需求。"
    else:
        try:
            with st.spinner("正在理解需求并筛选机会..."):
                st.session_state.search_result = run_brief_flow(user_query)
                st.session_state.retrieval_mode = os.environ.get("BRIEFFLOW_RETRIEVAL_MODE", "mock").strip().lower()
                st.session_state.searched_query = user_query
        except Exception:
            st.session_state.search_error = "检索失败，未生成结果。请检查后端配置后重试。"

result = st.session_state.get("search_result")
with st.sidebar:
    st.header("💼 BriefFlow")
    st.subheader("Agent Mode")
    if result:
        enhanced = result.get("summary_mode") == "llm"
        qwen_enhanced = (enhanced and result.get('summary_provider') == 'qwen'
                         and result.get('input_mode') == 'llm' and result.get('input_provider') == 'qwen')
        st.write("🟢 Qwen Enhanced" if qwen_enhanced else "🟡 Rule-based Fallback" if not enhanced or result.get('input_mode') != 'llm' else "🟢 LLM Enhanced")
        st.caption("AI-generated Brief" if enhanced else "Rule-based Brief")
        st.caption("本次摘要使用 LLM 选择经核实的事实措辞。" if enhanced else
                   "本次摘要由规则生成；未使用 LLM 摘要，或 LLM 调用未通过校验。")
        if enhanced and result.get('input_mode') != 'llm':
            st.caption("Input Agent 使用规则回退；摘要阶段使用 LLM。")
    else:
        st.write("尚未生成 Brief")
        st.caption("检索后显示本次实际摘要模式。")
    st.divider()
    st.info("修改需求后重新检索，即可生成新的机会简报。")
    st.caption("演示数据会明确标注。申请资格与截止日期请以官方来源为准。")

if st.session_state.get("search_error"):
    st.error(st.session_state.search_error)

if result is not None:
    if st.session_state.get("searched_query", user_query) != user_query:
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
    st.subheader("🤖 AI Brief")
    st.caption("AI-generated Brief" if result.get("summary_mode") == "llm" else "Rule-based Brief")
    st.info(result.get("summary") or "本次未生成摘要，请查看下方结果。")
    # These highlights are also computed, so legacy/missing optional fields are safe.
    st.caption(f"✦ {stats['high_match']} 条高匹配机会 · {stats['urgent_deadline']} 条 7 天内截止")

    st.subheader("🧠 Understood Preference")
    st.caption("已理解的筛选偏好 · 仅下列偏好参与筛选；本科资格等申请条件请查看来源核实。")
    preference = result.get("preference") or {}
    left, right = st.columns(2)
    for column, label, field in (
        (left, "📍 地点", "locations"), (right, "🎯 类型", "categories"),
        (left, "🔑 偏好", "keywords"), (right, "🚫 排除", "exclude_keywords"),
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
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(item.get("title") or "未命名机会")
                    organization = item.get("organization") or item.get("company") or "机构未注明"
                    st.write(organization)
                    st.caption(f"📍 {item.get('location') or '未注明'} · {item.get('category') or '未分类'}")
                    days = deadline_days(item, today)
                    deadline = item.get("deadline") or "未注明"
                    status = " · 已截止，请核实最新信息" if days is not None and days < 0 else (
                        " · 今天截止" if days == 0 else f" · {days} 天后截止" if days is not None and days <= 7 else "")
                    st.write(f"📅 截止：{deadline}{status}")
                    if is_high_match(item):
                        st.caption("✦ 高匹配 · Match Score ≥ 80")
                with col2:
                    st.metric("Match Score", item.get("match_score", "未提供"))
                    st.metric("Priority Score", item.get("priority_score", "未提供"))
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
                source_url = item.get("source_url") or item.get("link")
                if isinstance(source_url, str):
                    try:
                        url = urlsplit(source_url)
                        if url.scheme in ("http", "https") and url.hostname and not url.username and not url.password:
                            is_mock = "mock" in str(source).lower()
                            st.link_button("查看示例来源（Mock）" if is_mock else "查看原始来源", source_url)
                    except ValueError:
                        pass
