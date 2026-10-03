"""Run the mock pipeline: python backend/main.py (Python 3.10+)."""
import json
from pathlib import Path
import sys

# Support direct script execution as well as python -m backend.main.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.router.service import run_brief_flow

DEMO_REQUEST = "我是金融专业大三学生，想找粤港澳金融实习，不要销售岗。"


def main() -> None:
    result = run_brief_flow(DEMO_REQUEST)
    print("Preference:")
    print(json.dumps(result["preference"], ensure_ascii=False, indent=2))
    print(f"Top recommendations (showing up to 5 of {result['total_items']}; MOCK DATA):")
    for item in result["recommended_items"][:5]:
        print(f"- {item['job_id']} | {item['title']} | {item['location']}")
        print(f"  Match Score: {item['match_score']}")
        print(f"  Why Recommended: {'; '.join(item['why_recommended'])}")


if __name__ == "__main__":
    main()
