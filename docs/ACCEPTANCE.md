# Release acceptance

- [x] Clean image install from the version lock; wheel includes fixtures and browser assets, with hashes matching the workspace.
- [x] Full Linux suite passes: 92 tests including PostgreSQL integration, lineage, schema-impact, and semantic-guard regressions.
- [x] Reference fixture answers independently checked across multiple seeds.
- [x] Authentication, request validation, redacted errors, rate limits, and audit persistence verified.
- [x] Desktop/mobile browser flow checked; API error/empty readiness states covered by automated tests.
- [x] PostgreSQL rejects direct writes from the reader role; statement timeout and control isolation checked using current source.
- [x] Rebuilt demo container reports healthy on localhost; all 92 tests pass without mounting application source.
- [x] Non-root runtime, read-only application filesystem, and absent bootstrap credentials verified.
- [x] Local synthetic PostgreSQL backup/restore drill passes.
- [ ] Container image builds and reports ready using production configuration.
- [ ] Live DataHub ingestion/readback verified with a real instance.
- [ ] Live LLM request verified with a real key; model and metadata provenance recorded.
- [ ] Held-out baseline/context benchmark run; no synthetic-demo figures presented as model accuracy.
- [ ] TLS, backups, restore, secrets, and external health checks configured on selected host.

