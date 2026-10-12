# RC1 remote audit — 2026-10-12

`git fetch --all --prune` completed before inspection. Full commit SHAs,
ahead/behind counts and changed-file lists are in `branch-audit.json`.
Changed files are branch changes since the merge base with dev. main and dev
both resolve to 0743fe3, so the same feature comparison applies to both.

## Integration decisions

- integration/streamlit-agent-llm (7872fca): merge. Direct Python Router,
  optional input/output LLM, explicit summary_mode, deterministic fallback,
  Streamlit persistence/errors/source links, documentation and offline tests.
- feature/retrieval-round2 (2f65727): merge. Adds challenge-cup/CFFEX public
  sources, bounded parsing, standalone conservative date extraction and tests.
  Merge-tree compatibility check completed without conflicts.
- feature/main-router-frontend (8d6cc40): do not merge. app.py is superseded
  by integration, which also removes the unsupported feedback-memory claim.
- feature/agent-ao-llm (da386d3): do not merge. Integration contains the
  useful agents plus stronger timeout/configuration handling and provenance.
- feature/test-merge1 (f8397bb): do not merge. All 17 differing paths were
  compared with integration. app.py is identical to the superseded frontend
  branch; agent files regress JSON handling, validation and summary_mode.
  README/architecture/agent docs and tests regress integration coverage;
  requirements.txt is missing; package-lock loses platform metadata.
  Its unique Qwen endpoint/model defaults and forced test environment are
  configuration, not a new provider implementation. The test includes a
  hardcoded credential; no value is copied or used. Owner should revoke it.
- feature/flin-a3a4, feature/ranking-priority, feature/retrieval-database:
  already ancestors of dev; no unique commits to integrate.
- main/dev: unchanged upstream; dev is the RC base.

## Qwen finding

Qwen/compatible-mode configuration EXISTS in feature/test-merge1:
backend/llm.py and tests/test_agent_llm.py, model qwen3.7-plus, an Aliyun
compatible-mode endpoint. No dedicated DashScope implementation or verified
live Qwen invocation was established. RC retains the integration branch's
configurable OpenAI-compatible transport; unsafe provider defaults are not
copied. Qwen is not claimed as acceptance-tested.

## Known compatibility and scope

Old retrieval and Streamlit tests patch service.fetch_ukri; round2 switches
the service boundary to fetch_web. Adapt mocks while preserving assertions.
Streamlit -> Router -> Input -> Retrieval -> Ranking -> Output has no
localhost FastAPI dependency. backend/api.py remains an API interface.

Round2 does not actually resolve unspecified source location versus Ranking's
city hard filter. Its date extractor is not wired to detail-page crawling;
list-derived deadlines remain empty. These are documented upstream limits,
not silently represented as completed fixes. No ranking, database or crawler
logic is to be changed during the Output improvement phase.
