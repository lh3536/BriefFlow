import streamlit as st
import sys
from pathlib import Path

# 确保 app.py 在根目录时能正确导入 backend 模块
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.router.service import run_brief_flow

# 页面设置
st.set_page_config(page_title="BriefFlow 个人情报站", layout="wide")

# ---------------- 用户端界面 ----------------
st.title("🔍 BriefFlow AI 情报站")
st.markdown("### 一句话，创建属于你的 AI 情报站")

# 1. 用户输入
user_query = st.text_input(
    "请输入你的需求：",
    value="我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。"
)

# 2. 触发检索，并将结果存入 session_state 记忆体
if st.button("🚀 开始检索", type="primary"):
    with st.spinner('Agent 正在检索与筛选...'):
        # 调用后端，存入记忆缓存
        st.session_state.search_result = run_brief_flow(user_query)
        st.session_state.has_searched = True  # 标记已经检索过

# 3. 读取记忆，渲染结果（如果已经检索过）
if st.session_state.get("has_searched", False):
    result = st.session_state.search_result

    # 显示找到的总数
    st.success(f"已为你找到 {result['total_items']} 条机会")

    # 显示数量选择器（交互不会再导致页面重置）
    show_count = st.selectbox("展示数量", [5, 10, 20], index=0)

    # 循环渲染卡片
    for item in result["recommended_items"][:show_count]:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"{item['title']}")
                st.caption(f"📍 {item['location']} | 📅 {item.get('deadline', '未注明')}")
            with col2:
                st.metric(label="匹配分数", value=f"{item['match_score']}")

            with st.expander("💡 为什么推荐给你？"):
                for reason in item['why_recommended']:
                    st.write(f"- {reason}")

            # 反馈按钮
            if st.button(f"👎 不感兴趣", key=f"down_{item['job_id']}"):
                # 使用 st.toast，避免页面重刷时打断用户
                st.toast(f"已记录对《{item['title']}》的反馈，记忆已更新！", icon="✅")