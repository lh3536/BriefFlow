"""Deterministic deadline/date extraction, stdlib only.

规则：只认「截止 / 截至」语义 + 带年份的完整日期；缺年份、多日期冲突、无语义
一律返回空串，绝不猜测。输出 ISO 日期（YYYY-MM-DD）。
"""
from __future__ import annotations

import re
from datetime import date

_DEADLINE_HINTS = (
    "截止", "截至", "application close", "applications close",
    "applications are now open until", "on or before", "deadline",
)

# 带年份的日期 token（无年份的「月日」不算，避免拿抓取年份补齐）
_DATE_RE = re.compile(
    r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"   # 2026年5月23日
    r"|\d{4}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{1,2}"  # 2026-05-23 / 2026/5/23 / 2026.5.23
    r"|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}"
    r"|\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{4}"
    , re.IGNORECASE
)

_SENT_SPLIT = re.compile(r"[。；;！!\n]+")


def _to_iso(token: str) -> str:
    token = re.sub(r"\s+", "", token)
    match = re.fullmatch(r"(\d{4})[年\-/.](\d{1,2})[月\-/.](\d{1,2})日?", token)
    if match:
        parts = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    else:
        dmy = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", token)
        english = re.fullmatch(
            r"(\d{1,2})(January|February|March|April|May|June|July|August|September|October|November|December)(\d{4})",
            token, re.IGNORECASE,
        )
        if dmy:
            parts = (int(dmy.group(3)), int(dmy.group(2)), int(dmy.group(1)))
        elif english:
            months = {
                name.casefold(): month for month, name in enumerate(
                    ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1
                )
            }
            parts = (int(english.group(3)), months[english.group(2).casefold()], int(english.group(1)))
        else:
            return ""
    try:
        return date(*parts).isoformat()
    except ValueError:
        return ""


def extract_deadline(text: str) -> str:
    """从正文提取截止日期，返回 'YYYY-MM-DD' 或 ''。

    - 只在含「截止/截至」，或明确「报名时间……至……」的句子里找。
    - 一句话里有多个不同日期（如报名截止与初赛日期并列）无法确定 → 空串。
    - 只有「月日」而无年份 → 空串，不拿抓取年份补齐。
    """
    if not text:
        return ""
    for segment in _SENT_SPLIT.split(text):
        lowered = segment.casefold()
        explicit_registration_window = "报名时间" in segment and any(marker in segment for marker in ("至", "到"))
        if not any(hint in lowered for hint in _DEADLINE_HINTS) and not explicit_registration_window:
            continue
        tokens = {token for token in _DATE_RE.findall(segment) if token}
        if len(tokens) != 1:
            return ""
        return _to_iso(tokens.pop())
    return ""
