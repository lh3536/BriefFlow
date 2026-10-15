# Retrieval / Database V0.2

`get_items(preference)` supports `mock` (default), `database` and `web` modes.
All sources pass through normalization, validation and deterministic deduplication.
Six bounded public sources are connected: UKRI funding opportunities, the
Challenge Cup website, the China Financial Futures Exchange, HKEX Early
Careers, the Macao Government Information Bureau feed and the Hong Kong SFC
internship pages. Web mode aggregates all six through `fetch_web`; a failure
in one source does not discard successful records from the others.

Run `python -m backend.retrieval --mode mock` for JSON output and retrieval metrics.
See [RETRIEVAL_DATABASE.md](../../docs/RETRIEVAL_DATABASE.md) for setup and limitations.
