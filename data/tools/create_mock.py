"""One-off synthetic fixture generation; no external data sources."""
import json
from pathlib import Path

opportunities = [
    ("投行分析实习", "广州", "金融实习", "2026-10-20"),
    ("行业研究实习", "深圳", "金融实习", "2026-10-25"),
    ("资产管理实习", "香港", "金融实习", "2026-11-05"),
    ("风险管理实习", "澳门", "金融实习", "2026-11-10"),
    ("量化研究实习", "深圳", "金融实习", "2026-11-15"),
    ("金融科技产品实习", "广州", "金融实习", "2026-11-20"),
    ("金融数据分析实习", "香港", "金融实习", "2026-11-25"),
    ("资产管理运营实习", "澳门", "金融实习", "2026-12-01"),
    ("企业战略分析实习", "深圳", "金融实习", "2026-12-05"),
    ("企业估值案例挑战赛", "广州", "经管比赛", "2026-10-28"),
    ("绿色金融商业方案赛", "澳门", "经管比赛", "2026-11-18"),
    ("金融研究夏令营预报名", "香港", "夏令营", "2026-12-10"),
    ("计量经济学夏令营预报名", "广州", "夏令营", "2026-12-20"),
    ("公司金融研究助理", "深圳", "科研机会", "2026-10-30"),
    ("跨境金融研究助理", "香港", "科研机会", "2026-12-31"),
]
data = []
for i, (title, city, category, deadline) in enumerate(opportunities, 1):
    timing = 12 if deadline < "2026-11-01" else 8 if deadline < "2026-12-01" else 5
    data.append({
        "job_id": f"job_{i:03d}", "title": f"【模拟】{title}",
        "company": f"虚构机构·BriefFlow示范{i:02d}", "location": city,
        "category": category, "deadline": deadline,
        "link": f"https://example.com/job_{i:03d}", "match_score": 80 + timing,
        "why_recommended": [f"目标地点匹配（{city}）+30", "金融学专业与机会主题匹配+25", "模拟设定接受大三本科生+15", "职责与目标兴趣匹配且通过排除规则+10", f"以2026-10-03为基准按截止月份评估时效+{timing}"],
    })
(Path(__file__).resolve().parents[1] / "mock" / "mock_db.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
