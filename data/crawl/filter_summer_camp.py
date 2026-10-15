"""从 1599 条夏令营里筛选 40 条，自动补 BriefFlow 字段。"""
import json
import re
from pathlib import Path

RAW = Path(__file__).parent / "summer_camp_raw.json"
OUT = Path(__file__).parent / "summer_camp_filtered.json"

# 学科分类关键词
DISCIPLINE_RULES = {
    "计算机": ["计算机", "软件", "人工智能", "数据", "信息", "智能", "电子", "自动化", "网络"],
    "金融经济": ["金融", "经济", "会计", "财政", "五道口", "经管", "管理科学"],
    "生物医学": ["生物", "医学", "药", "生命", "公共卫生", "临床", "健康", "医"],
    "理工科": ["数学", "物理", "化学", "材料", "机械", "工程", "力学", "航天", "核",
              "环境", "能源", "建筑", "土木", "航空", "精密仪器", "工业工程", "船舶"],
    "法政社科": ["法", "政治", "社会", "国际关系", "公共管理", "苏世民", "国际"],
    "人文艺术": ["文", "历史", "哲学", "艺术", "新闻", "外国语", "美术", "音乐"],
    "管理商科": ["管理", "商", "市场", "MBA", "经济管理", "工商"],
    "通用": [],
}

# 城市推断：具体城市优先，学校名兜底。顺序很重要！
CITY_RULES = [
    ("深圳", ["深圳", "南方科技", "哈工大深圳"]),
    ("香港", ["香港", "港大", "港科", "港中", "港理工", "港城"]),
    ("澳门", ["澳门"]),
    ("广州", ["中山大学", "华南理工", "暨南大学", "广州"]),
    ("上海", ["复旦大学", "上海交大", "同济", "华东师范", "上海"]),
    ("杭州", ["浙江大学", "杭州"]),
    ("南京", ["南京大学", "东南大学", "南京"]),
    ("武汉", ["武汉", "华中科技", "武汉大学"]),
    ("成都", ["四川大学", "成都", "电子科技"]),
    ("西安", ["西安", "西交", "西工大"]),
    ("天津", ["天津", "南开", "天大"]),
    ("厦门", ["厦门", "厦大"]),
    ("长沙", ["长沙", "中南大学", "湖南大学"]),
    ("合肥", ["合肥", "中国科学技术大学"]),
    ("北京", ["清华", "北大", "北京", "人大", "北航", "北理", "北师", "中国科学院"]),
]

PER_DISCIPLINE = 5


def classify(title: str) -> str:
    for disc, keywords in DISCIPLINE_RULES.items():
        if any(k in title for k in keywords):
            return disc
    return "通用"


def infer_city(title: str) -> str:
    for city, keywords in CITY_RULES:
        if any(k in title for k in keywords):
            return city
    return "多个城市"


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    picked = {}
    used_titles = set()

    for item in raw:
        title = item["title"].strip()
        if title in used_titles:
            continue
        disc = classify(title)
        if len(picked.get(disc, [])) >= PER_DISCIPLINE:
            continue
        # 优先大湾区
        city = infer_city(title)
        used_titles.add(title)
        picked.setdefault(disc, []).append({
            "title": title,
            "link": item["link"],
            "disciplines": [disc],
            "location": city,
        })

    # 展平成 BriefFlow 格式
    out = []
    idx = 7001
    for disc, items in picked.items():
        for it in items:
            out.append({
                "job_id": f"job_{idx}",
                "module": "summer_camp",
                "category": "夏令营",
                "disciplines": it["disciplines"],
                "grades": ["大三"],
                "time_pref": "暑期",
                "title": it["title"],
                "company": "某高校",
                "location": it["location"],
                "deadline": "2026-12-31",
                "link": it["link"],
                "summary": it["title"] + "。",
                "requirements": ["相关专业大三学生"],
                "tags": ["夏令营"] + it["disciplines"],
            })
            idx += 1

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"筛选出 {len(out)} 条")
    for disc, items in picked.items():
        print(f"{disc}: {len(items)} 条")


if __name__ == "__main__":
    main()