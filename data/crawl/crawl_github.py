"""抓取 GitHub 上的 awesome 列表 Markdown，提取标题+链接。"""
import re
import json
from pathlib import Path
import requests

# 换你要抓的仓库
REPO = "shenyanpai/awesome-summer-camp-2026"
BRANCH = "main"  # 有些仓库用 master
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/README.md"


def fetch_markdown(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (BriefFlow data collection)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_links(md: str) -> list[dict]:
    """从 Markdown 里提取 [title](url) 形式的链接。"""
    pattern = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")
    items = []
    seen = set()
    for title, url in pattern.findall(md):
        title = title.strip()
        if not title or url in seen:
            continue
        # 过滤掉导航类链接
        if any(skip in url for skip in ("github.com", "shields.io", "badge")):
            continue
        seen.add(url)
        items.append({"title": title, "link": url, "source": REPO})
    return items


if __name__ == "__main__":
    md = fetch_markdown(RAW_URL)
    items = extract_links(md)
    out = Path(__file__).parent / "summer_camp_raw.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"抓到 {len(items)} 条，保存到 {out}")
    for item in items[:10]:
        print(item["title"], "->", item["link"])