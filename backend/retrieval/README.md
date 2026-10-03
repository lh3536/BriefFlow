# Retrieval / Database V0.1

`get_items(preference)` supports `mock` (default), `database` and `web` modes.
All sources pass through normalization, validation and deterministic deduplication.
One public RSS source is connected: UKRI funding opportunities.

Run `python -m backend.retrieval --mode mock` for JSON output and retrieval metrics.
See [RETRIEVAL_DATABASE.md](../../docs/RETRIEVAL_DATABASE.md) for setup and limitations.
