# Final team integration audit (2026-10-14)

Base: origin/dev = release/brief-flow-rc2 = 991c1aa5ac1e39ecf1506290739e0502a17789c5.
All remote refs fetched with --all --prune before branching.

| Remote branch | Head | Ahead / behind dev | Decision |
|---|---|---|---|
| dev | 991c1aa | 0 / 0 | Stable base |
| main | 0743fe3 | 0 / 9 | Ancestor; unchanged |
| feature/agent-ao-llm | da386d3 | 2 / 11 | Superseded by integration and RC2 validated agents |
| feature/flin-a3a4 | 69a3979 | 0 / 11 | Already included |
| feature/main-router-frontend | 8d6cc40 | 2 / 9 | Older app superseded by integrated RC2 UI |
| feature/ranking-priority | d0d2654 | 0 / 12 | Already included, retain RC2 calibration unchanged |
| feature/retrieval-database | 0efa453 | 0 / 13 | Already included |
| feature/retrieval-round2 | 2dcf842 | 1 / 7 | Merge owner final detail-evidence implementation unchanged |
| feature/test-merge1 | f8397bb | 6 / 9 | Older duplicate agents/UI and unsafe historical credential; exclude |
| integration/streamlit-agent-llm | 7872fca | 0 / 6 | Already included |
| release/brief-flow-rc1 | 291c4e5 | 0 / 1 | Already included |
| release/brief-flow-rc2 | 991c1aa | 0 / 0 | Already included |

The only additional merge is retrieval-round2 2dcf84213226158076b822d7c82609cd9beb607d.
No conflicts. Its existing fetch_web test-boundary adaptation was already present in RC2.
No new adapters were needed: get_items -> rank_items -> build_brief contracts agree.
The merged retrieval sources.py and dates.py match the owner branch byte-for-byte.
No integration-authored changes to module internals, prompts, scoring, provider configuration,
.env.example, Router, database schema or UI. The owner's completed crawler changes are imported,
not redesigned. Historical test-merge1 credential is excluded and still requires revocation.

Validation: Python 170 passed plus 142 subtests; Frontend 13 passed; no failed tests.
Mock validation, frontend production build and backend/main.py pass.
Test environment uses workspace TEMP/TMP and prewarms Streamlit before unchanged test suite.
Real LLM requests disabled for validation; .env not modified. Qwen configuration retained.

Streamlit servers launched in mock and web modes on local ports 8511 and 8512.
Browser acceptance is limited by Edge launch failure and in-app browser localhost timeout.
See final report for independent AppTest end-to-end results and delivery status.

Independent AppTest end-to-end acceptance (real Router, no mocked pipeline):
- Mock request: 15 retrieved, 11 recommended, deterministic brief, Mock Data displayed.
- Web request: 33 retrieved from real sources, 13 recommended, Web Data displayed,
  zero Mock records and no retrieval fallback. Real Qwen was not requested.
- Both rendered preferences, summary, metrics and cards without Streamlit exceptions.
- Standalone server processes remain running, but localhost health/browser connections
  time out in this environment; visual browser acceptance remains unverified.
- Current staged tree scan: no credential findings; .env ignored and not tracked;
  .env.example key is blank. No values from historical credentials were copied.
