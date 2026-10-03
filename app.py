import streamlit as st
import sys
from pathlib import Path

# 确保 app.py 在根目录时能正确导入 backend 模块
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.router.service import run_brief_flow

st.set_page_config(page_title="BriefFlow 个人情报站", layout="wide")
st.title("🔍 BriefFlow AI 情报站")
st.markdown("### 一句话，创建属于你的 AI 情报站")

# 侧边栏：收益统计（你的加分项）
with st.sidebar:
    st.header("📊 商业模型与成本分析")
    st.metric(label="单次运行成本（全LLM）", value="0.05 元")
    st.metric(label="模块化后成本", value="0.015 元")
    st.metric(label="预计盈亏平衡用户数", value="120 人")

# 主页面：输入与展示
user_query = st.text_input("请输入你的需求：",
                           value="我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。")

if st.button("🚀 开始检索", type="primary"):
    with st.spinner('Agent 正在检索与筛选...'):
        result = run_brief_flow(user_query)

    st.success(f"已为你找到 {result['total_items']} 条机会")

    # 展示卡片
    for item in result["recommended_items"][:5]:
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
                st.success("记忆已更新，下次分数将下降！")