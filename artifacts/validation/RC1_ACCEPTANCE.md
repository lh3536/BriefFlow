# BriefFlow RC1 validation

Release branch: release/brief-flow-rc1. Base: origin/dev 0743fe3.
Integrated integration/streamlit-agent-llm 7872fca and
feature/retrieval-round2 2f65727 with explicit merge commits.

## Sequence and evidence

Audit -> Combine -> Test -> Launch -> Baseline screenshots -> Output review
and improvement -> Full retest -> Improved screenshots -> Report.

| Check | Baseline after integration fix | Improved |
|---|---|---|
| Python (`python -m pytest tests -q`) | 135 passed / 0 failed | 152 passed / 0 failed |
| Additional unittest subtests | 133 passed | 142 passed |
| Frontend (`vitest run`) | 13 passed / 0 failed | 13 passed / 0 failed |
| Mock validation | PASS | PASS |
| Frontend production build | PASS | PASS |
| `python backend/main.py` | PASS | PASS |
| Streamlit AppTest + actual browser | PASS | PASS |

Combined primary test counts: baseline 148 passed / 0 failed; improved
165 passed / 0 failed. Subtests are reported separately, not double counted.
One third-party Starlette/httpx deprecation warning remains, with no failures.

Initial integration tests had 9 failures (128 passed), all old fetch_ukri mock
targets. The service now calls fetch_web; only the mock targets were adapted,
preserving assertions. Environment-only issues were resolved separately:
use workspace temporary directories and scope test discovery to repository
tests, excluding locally installed dependency packages.

Screenshot files are in ../screenshots/:
01_baseline_top.png, 02_baseline_results.png,
03_improved_top.png, 04_improved_results.png.
They are actual browser screenshots of the same supplied request. Waits ensure
metrics and expanded baseline reasons are fully rendered. No video or PPT.

## Scope and remaining acceptance boundaries

- `backend/ranking` is byte-identical to dev.
- `backend/retrieval` is byte-identical to feature/retrieval-round2.
  Retrieval changed only by integrating that audited branch.
- backend/api.py and frontend/package-lock.json are unchanged from dev.
- Live Qwen and live public-source availability are not certified by offline
  tests. Qwen-compatible configuration exists in test-merge1 but is not merged.
  Its exposed credential requires owner revocation; it was not copied or used.
- Upstream rules do not independently validate undergraduate eligibility or
  recognize all requested keywords; the UI now makes this visible.
- Public sources with unknown locations may be filtered out by existing city
  rules. Round2 date extraction is not connected to detail-page crawling.
- No blocking failure remains for this Mock/fallback RC acceptance scope.

## Reproduce

Install requirements.txt and backend/requirements.txt plus pytest in Python
3.10+; install frontend dependencies with npm ci. Run pytest tests -q, the mock
validation script, backend/main.py, npm test and npm run build from frontend.
Run streamlit run app.py (FastAPI is not needed).

This host used bundled Python 3.12 with isolated packages under ignored work/,
Node with locked npm dependencies, and local Edge in headless mode for screenshots.
Its Streamlit launch additionally set --global.developmentMode false,
--server.headless true, --server.address 127.0.0.1, --server.port 8501 and
--browser.gatherUsageStats false. Final local site remains running for review.
