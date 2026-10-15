# RC2 final product validation — 2026-10-13 (Asia/Shanghai)

Base: release/brief-flow-rc1 at 291c4e515ce9a4d08a80a7d200660842585d78f0.
Only release/brief-flow-rc2 is modified. No UI redesign, video or presentation.

## Qwen implementation and actual validation boundary

Reused the existing urllib OpenAI-compatible client. Default base URL is now
https://dashscope.aliyuncs.com/compatible-mode/v1 and model is qwen-plus.
BRIEF_LLM_API_KEY remains optional and external; .env is ignored and the example
contains an empty key. Alternative compatible endpoints remain configurable.

All remote branches were fetched (HTTP/1.1 succeeded after initial connection
failures) and scanned. The test-merge1 branch contains old Qwen defaults and a
credential in tests/test_agent_llm.py:11. That file/credential was neither
copied nor used. No credential values are included in reports. Owner revocation
is still needed. RC1's safer client is used instead of merging old code.

Real Qwen test: NOT RUN. Neither a repo-root .env nor an environment key exists.
No real Qwen preference or Qwen-generated brief is claimed, and screenshots
05_rc2_qwen_top.png / 06_rc2_qwen_results.png are deliberately not generated.
Offline transport tests cover the requested complete preference, Qwen endpoint,
synonyms, both-agent success, partial failure, total failure and absent key.
Input prompt now explicitly retains 金融 / 券商 / 投行 / FinTech and both requested
categories. Output keeps RC1's validated factual sentence selection, 2–4 sentences.

After configuring a valid key locally in ignored .env, rerun
`python scripts/validate_rc2_live.py`. It never prints credentials, performs live
calls only with a configured Qwen provider, and writes qwen-live.json plus the
independent real Web pipeline report. A Qwen screenshot still requires actual
PASS and a fresh browser run; mocked test success is never sufficient.

Qwen Enhanced requires successful validated Input AND Output with Qwen provider
metadata for the current run. API-key presence alone cannot activate it. Partial
failure is disclosed as Rule-based Fallback while retaining truthful summary_mode.

## Actual public-source probe and pipeline

Initial independent real source requests: UKRI 20 accepted, 挑战杯 12 accepted,
中金所 1 accepted; zero failed sources. Total 33 (see web-probe.json).
Subsequent complete Router requests independently fetched live data: the exact
four-city demo request retrieved 32 records and returned 0 after filtering;
the broader query 金融比赛 retrieved 33 and returned 13. Counts are separate live
runs and are not presented as one immutable snapshot. Neither used Mock fallback.

Source provenance is now captured before Ranking, so a successful Web fetch
followed by zero matches still displays Web Data. Actual record count is shown
with the empty state. Unknown locations are not fabricated or treated as cities.
Official records may be news, closed events or funding announcements: the UI
explicitly does not claim every record is an open, undergraduate-eligible offer.

The newer retrieval-round2 commit 2dcf842 was inspected, including bounded detail
enrichment. RC2 retains RC1's working source adapters; no new crawler expansion
or database change was needed for this acceptance scope.

## Ranking diagnosis and minimal calibration

Before changing policy, five requested queries plus the exact demo query were
run without LLM on the unmodified Mock dataset, with 2026-10-13 as_of date.
See ranking-before.json and ranking-after.json for preferences and item breakdowns.

| Query | Total | Before min/median/max | Before high | Before priority | After min/median/max | After high | After priority |
|---|---:|---|---:|---|---|---:|---|
| 粤港澳金融实习 | 9 | 100/100/100 | 9 | 80–86 | 100/100/100 | 9 | 80–86 |
| 香港 FinTech 比赛 | 0 | N/A | 0 | N/A | N/A | 0 | N/A |
| 深圳投行实习 | 3 | 80/80/80 | 3 | 64–67 | 70/70/70 | 0 | 56–59 |
| 澳门科研机会 | 0 | N/A | 0 | N/A | N/A | 0 | N/A |
| 金融机会但不要销售 | 13 | 20/20/20 | 0 | 16–22 | 30/30/30 | 0 | 24–30 |
| Exact demo request | 11 | 80/100/100 | 11 | 64–86 | 70/85/100 | 10 | 56–86 |

This is NOT solely a Mock dataset issue: hard location/category matches supplied
an automatic 80 (already High Match), and ANY single keyword supplied all 20
keyword points. The Shenzhen investment-banking query had zero matching direction
keywords yet all three records were labeled high match.

Minimal correction: location/category/keyword weights 40/40/20 -> 35/35/30;
keyword contribution = keyword weight × matched/requested keyword count.
No hard filter, time bonus, tie-breaker, High Match threshold or dataset changed.
Reasons retain exact scored contributions and now show keyword coverage.
Controlled tests verify full/half/no keyword coverage = 100/85/70, reason sums,
custom weights, and priority calculations. A broad one-keyword request can still
legitimately score 100 across these homogeneous Mock entries; no artificial noise.

Without Qwen, the existing rule parser still omits FinTech/券商. The five-query
audit is explicitly a rule-mode audit, not evidence of Qwen understanding.

## Final regression and security

Python: 166 passed / 0 failed (+142 subtests).
Frontend: 13 passed / 0 failed. Total primary tests: 179 passed / 0 failed.
Mock Validation, frontend production build, backend/main.py and Streamlit AppTest
pass. A third-party Starlette/httpx deprecation warning remains.

Real browser Web screenshot: artifacts/screenshots/07_rc2_web_results.png,
using query 金融比赛, with real official-source results and Rule-based Fallback.
The final screenshot's independent fetch returned 12 matches (the earlier live
script returned 13); browser-web.txt records that exact screenshot run. These are
live snapshots, not replayed fixtures or counts forced to agree across requests.
The exact supplied query is also browser-tested and correctly shows zero matches
with Web Data provenance. Qwen screenshots remain unavailable for lack of key.

Current tracked tree: no credential findings; .env ignored; .env.example safe.
Remote historical finding is recorded by file/line/type only in security-final.json.

Remaining blocker for real-model acceptance: a valid locally configured Qwen key
and successful live Input/Output call. The four-city real-opportunity demo also
has a coverage limitation: current sources don't supply confirmed city/eligibility
metadata. This is disclosed, not masked by ranking changes or manufactured data.
