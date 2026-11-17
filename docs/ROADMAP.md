# Roadmap

## First working release

- [x] Modular query pipeline, analyst UI, demo fixture, adapter contracts, SQL safety checks, durable audit, and deployment configuration.
- [x] Parser bypass cases, reference metrics across seeds, authentication, rate limiting, body limits, error redaction, and database privilege boundaries verified.
- [x] Desktop/mobile browser checks and local PostgreSQL backup/restore drill.
- [x] Final corrected package image verified without source mounts; localhost HTTP smoke checks and source/asset fingerprints pass.

## Before a production claim

- Packaged demo and real PostgreSQL role/execution tests pass; production mode remains dependent on the live connections below.
- Exercise live DataHub ingestion/readback.
- Exercise a real model request with user-provided credentials; document model/version and actual failure cases.
- Add 30–50 reviewed questions with a genuinely separated held-out split. The initial development suite is not held out.
- Run schema-only vs metadata experiments with the same model, fixture seeds, and prompts apart from the intended context change. Record cost, latency, answer correctness, clarification, and refusal behavior.
- [x] SQL-derived column lineage display and query-scoped schema-impact inspection. Reading estate-wide lineage from live DataHub remains pending.
- Select a production host, set TLS/secrets, pin image digests, scan the build, and test backup/restore.

## Later, if justified

OIDC/user accounts, per-user authorization, richer observability, change-impact analysis, retrieval benchmarks, larger warehouse scenarios, and streaming responses. Do not add Kafka, Kubernetes, or a vector store without a demonstrated requirement.

