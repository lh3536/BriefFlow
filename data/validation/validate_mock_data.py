"""Validate BriefFlow seed data across six modules, eight disciplines, and grades."""
import json
from pathlib import Path
import re

REQUIRED = {
    "job_id", "module", "title", "company", "location", "category",
    "deadline", "link", "disciplines", "grades", "time_pref",
}
MODULES = {"internship", "summer_camp", "research", "competition", "summer_school", "scholarship"}
CATEGORIES = {"实习", "夏令营", "科研", "竞赛", "暑校", "奖学金"}
DISCIPLINES = {"金融经济", "管理商科", "计算机", "理工科", "生物医学", "法政社科", "人文艺术", "通用"}
GRADES = {"大一", "大二", "大三", "大四", "研究生", "不限"}
TIME_PREFS = {"暑期", "寒假", "日常", "长期", "不限"}
LOCATIONS = {
    # P0 大湾区重点
    "广州", "深圳", "香港", "澳门", "珠海",
    # P1 大湾区其他
    "佛山", "东莞", "中山", "惠州", "江门", "肇庆",
    # P2 全国主要城市
    "北京", "上海", "杭州", "南京", "武汉", "成都", "西安",
    "天津", "重庆", "苏州", "厦门", "长沙", "青岛", "合肥",
    # 特殊类型
    "全国", "线上", "多个城市",
}
FORBIDDEN = ("销售", "销售代表", "客户经理销售方向", "电话营销", "地推", "客服", "保险代理")


def validate(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    errors: list[str] = []
    if not isinstance(data, list):
        return ["Root must be a list"]

    ids = []
    modules_seen, disciplines_seen = set(), set()
    for i, row in enumerate(data, 1):
        label = f"Record {i}"
        if not isinstance(row, dict):
            errors.append(f"{label}: not a dict")
            continue
        missing = REQUIRED - set(row)
        if missing:
            errors.append(f"{label}: missing fields {sorted(missing)}")
            continue

        ids.append(row["job_id"])
        modules_seen.add(row["module"])
        disciplines_seen.update(row["disciplines"] if isinstance(row["disciplines"], list) else [])

        if row["module"] not in MODULES:
            errors.append(f"{label}: invalid module {row['module']}")
        if row["category"] not in CATEGORIES:
            errors.append(f"{label}: invalid category {row['category']}")
        if row["location"] not in LOCATIONS:
            errors.append(f"{label}: invalid location {row['location']}")

        if not isinstance(row["disciplines"], list) or not row["disciplines"]:
            errors.append(f"{label}: disciplines must be nonempty list")
        else:
            for d in row["disciplines"]:
                if d not in DISCIPLINES:
                    errors.append(f"{label}: invalid discipline {d}")

        if not isinstance(row["grades"], list) or not row["grades"]:
            errors.append(f"{label}: grades must be nonempty list")
        else:
            for g in row["grades"]:
                if g not in GRADES:
                    errors.append(f"{label}: invalid grade {g}")

        if row["time_pref"] not in TIME_PREFS:
            errors.append(f"{label}: invalid time_pref {row['time_pref']}")

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row["deadline"])):
            errors.append(f"{label}: invalid deadline format")

        if not str(row["link"]).startswith("http"):
            errors.append(f"{label}: link must start with http")

        if any(word in json.dumps(row, ensure_ascii=False) for word in FORBIDDEN):
            errors.append(f"{label}: forbidden keyword")

    if len(ids) != len(set(ids)):
        errors.append("Duplicate job_id")

    print(f"共 {len(data)} 条")
    print(f"模块覆盖: {sorted(modules_seen)}")
    print(f"学科覆盖: {sorted(disciplines_seen)}")
    return errors


if __name__ == "__main__":
    try:
        failures = validate(Path(__file__).resolve().parents[1] / "mock" / "mock_db.json")
    except (OSError, ValueError) as exc:
        failures = [str(exc)]
    if failures:
        print("FAIL:")
        for f in failures:
            print("  - " + f)
        raise SystemExit(True)
    print("PASS")