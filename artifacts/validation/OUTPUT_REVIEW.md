# OUTPUT REVIEW — captured before improvement

Browser: actual local Streamlit at http://localhost:8501, Edge/Playwright,
1440 × 1100, 2026-10-12 Asia/Shanghai. No API server was started.

Request used for both baseline and improved screenshots:

> 我是金融专业大三学生，想找广州、深圳、香港、澳门适合本科生的金融、券商、投行和 FinTech 机会，优先实习和比赛，不要销售岗位。

1. Brief repeats counts in one sentence without useful first actions or timing.
2. English preference labels are less readable; parsed keywords only include
   金融/投行, and undergraduate eligibility is not a structured filter. The UI
   should show the actual understanding rather than imply full comprehension.
3. Scores have no plain explanation or high-match distinction.
4. Reasons are hidden and primarily read as arithmetic contributions.
5. Sidebar mode reflects key availability, not actual summary success. Mock
   links should explicitly say they are example sources.

## Implemented after baseline

- Factual 2–4 sentence brief with up to two existing non-expired item titles,
  accurate counts, applicable deadline reminders, and a Mock disclaimer.
- Additive highlights and result_stats; all five existing fields retained.
- LLM chooses only approved factual wording. Invalid prose, extra claims,
  wrong indices or network failure fall back; model text is never displayed
  unchecked. This deliberately limits creative wording to guarantee grounding.
- Chinese structured preferences with an explicit qualification-check limit.
- Four counters calculated from the actual full returned list, not the visible
  five cards or model metadata. High match: finite score 80–100. Urgent:
  deadline 0–7 days away, inclusive, using Beijing date; expired/unknown excluded.
- Readable card hierarchy, visible reasons, high-match badges, deadline status,
  plain score explanations and clearly marked Mock example links.
- Actual summary_mode controls AI-generated Brief / Rule-based Brief labels.
  Observed Mock fallback is explicit. Empty live results do not claim verified
  provenance because the unchanged retrieval contract lacks that evidence.
- No ranking/retrieval/database/crawler logic was edited in this phase.

Both browser runs returned 11 Mock opportunities, 11 high matches and no
deadline within seven days on 2026-10-12. No real LLM credentials were used.
