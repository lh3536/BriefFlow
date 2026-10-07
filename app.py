"""Competition demo: call the Python Router directly."""
import os
from urllib.parse import urlsplit
import streamlit as st
from backend.llm import llm_available
from backend.router.service import run_brief_flow

st.set_page_config(page_title="BriefFlow 个人情报站", page_icon="💼", layout="wide")
st.title("🔍 BriefFlow")
st.caption("一句话，创建属于你的 AI 情报站")
with st.sidebar:
    st.header("💼 BriefFlow")
    st.subheader("Agent Mode")
    st.write("🟢 LLM Enhanced" if llm_available() else "🟡 Rule Fallback")
    st.caption("LLM Enhanced 表示已配置；调用失败时自动回退。")
    st.divider()
    st.info("💡 修改输入，点击检索，Agent 会为你重新定制机会。")

user_query = st.text_input("请输入你的需求：", value="我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。")
if st.button("🚀 开始检索", type="primary"):
    st.session_state.pop("search_result", None)
    st.session_state.pop("search_error", None)
    if not user_query.strip():
        st.session_state.search_error = "请输入检索需求。"
    else:
        try:
            with st.spinner("Agent 正在检索与筛选..."):
                st.session_state.search_result = run_brief_flow(user_query)
                st.session_state.retrieval_mode = os.environ.get("BRIEFFLOW_RETRIEVAL_MODE", "mock").strip().lower()
        except Exception:
            # Raw exception strings may contain endpoint credentials.
            st.session_state.search_error = "检索失败，未生成结果。请检查后端配置后重试。"
if st.session_state.get("search_error"):
    st.error(st.session_state.search_error)
if "search_result" in st.session_state:
    result = st.session_state.search_result
    items = result["recommended_items"]
    mock_data = any("mock" in str(item.get("source", "")).lower() for item in items)
    if mock_data or st.session_state.get("retrieval_mode") == "mock":
        st.warning("Demo / Mock Data：模拟机会，非真实招聘信息。")
        if st.session_state.get("retrieval_mode") != "mock":
            st.warning("所选数据源未返回可用数据，Retrieval 已回退到 Mock Data。")
    st.success(f"已为你找到 {result['total_items']} 条机会")
    st.subheader("🤖 AI Brief")
    st.caption("LLM Summary" if result.get("summary_mode") == "llm" else "Deterministic Fallback Summary")
    st.info(result["summary"])
    st.subheader("🧠 Understood Preference")
    preference = result["preference"]
    for label, field in (("Locations", "locations"), ("Categories", "categories"),
                         ("Keywords", "keywords"), ("Excluded", "exclude_keywords")):
        st.write(f"{label}: {' / '.join(preference.get(field, [])) or '未指定'}")
    show_count = st.selectbox("展示数量", [5, 10, 20], index=0)
    for item in items[:show_count]:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(item.get("title") or "未命名机会")
                organization = item.get("organization") or item.get("company")
                if organization:
                    st.write(organization)
                st.caption(f"📍 {item.get('location') or '未注明'} | {item.get('category') or '未分类'} | 📅 {item.get('deadline') or '未注明'}")
            with col2:
                st.metric("匹配分数", item.get("match_score", "未提供"))
                if item.get("priority_score") is not None:
                    st.metric("优先级分数", item.get("priority_score"))
            with st.expander("💡 为什么推荐给你？"):
                reasons = item.get("why_recommended") or []
                if isinstance(reasons, str):
                    reasons = [reasons]
                for reason in reasons:
                    st.write(f"- {reason}")
            st.caption(f"来源：{item.get('source') or '未注明'}")
            source_url = item.get("source_url") or item.get("link")
            if isinstance(source_url, str):
                try:
                    url = urlsplit(source_url)
                    if url.scheme in ("http", "https") and url.hostname and not url.username and not url.password:
                        st.link_button("查看来源", source_url)
                except ValueError:
                    pass
