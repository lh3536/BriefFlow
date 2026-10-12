"""Deterministic deadline/date extraction, stdlib only.

规则：只认「截止 / 截至」语义 + 带年份的完整日期；缺年份、多日期冲突、无语义
一律返回空串，绝不猜测。输出 ISO 日期（YYYY-MM-DD）。
"""
from __future__ import annotations

import re
from datetime import date

_DEADLINE_HINTS = ("截止", "截至")

# 带年份的日期 token（无年份的「月日」不算，避免拿抓取年份补齐）
_DATE_RE = re.compile(
    r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"   # 2026年5月23日
    r"|\d{4}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{1,2}"  # 2026-05-23 / 2026/5/23 / 2026.5.23
)

_SENT_SPLIT = re.compile(r"[。；;！!\n]+")


def _to_iso(token: str) -> str:
    token = re.sub(r"\s+", "", token)
    match = re.fullmatch(r"(\d{4})[年\-/.](\d{1,2})[月\-/.](\d{1,2})日?", token)
    if not match:
        return ""
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
    except ValueError:
        return ""


def extract_deadline(text: str) -> str:
    """从正文提取截止日期，返回 'YYYY-MM-DD' 或 ''。

    - 只在含「截止/截至」的句子里找。
    - 一句话里有多个不同日期（如报名截止与初赛日期并列）无法确定 → 空串。
    - 只有「月日」而无年份 → 空串，不拿抓取年份补齐。
    """
    if not text:
        return ""
    for segment in _SENT_SPLIT.split(text):
        if not any(hint in segment for hint in _DEADLINE_HINTS):
            continue
        tokens = {token for token in _DATE_RE.findall(segment) if token}
        if len(tokens) != 1:
            return ""
        return _to_iso(tokens.pop())
    return ""
