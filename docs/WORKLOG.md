# Work log

## 2026-11-15 — Project initiation

- Reviewed the DataHub India overview and agreed on a metadata-aware SQL agent with reliability evaluation.
- User requested deployability, production-oriented implementation, and maintained Markdown records.
- User accepted OpenAI-compatible API and Docker defaults.
- Inspected workspace: no existing repository or application. Existing PDF-review scratch assets preserved.
- Python 3.12 and common dependencies are available. Docker CLI is installed, but its Linux daemon is stopped.
- Created architecture, product record, decisions, bug register, learnings, security model, and delivery checklist.
- Impeccable context launcher could not initialize its external cache. Used documented fallback and recorded interface decisions in DESIGN.md.

## 2026-11-15 — Implementation and first verification

- Implemented the analyst workbench, separate metadata/model adapters, SQL AST policy, bounded execution, authentication, durable audit/rate limiting, and a deterministic synthetic fixture.
- Added container deployment, PostgreSQL role initialization, CI definition, DataHub ingestion tooling, operational documentation, and browser smoke scripts.
- First regression pass: 78 passed, one PostgreSQL test skipped locally; development fixture report: 18/18 checks across three seeds. These are not model-accuracy results.
- Fixed CTE qualification, SQLite COUNT authorization, PostgreSQL integral Decimal serialization, and Boolean AST function-classification issues. Stable defect records are in BUGS.md.
- First image built successfully and initialized the PostgreSQL volume. Host port 8000 was occupied; changed the Docker host port to configurable 8088 without touching the other service.
- Dependency downloads are unusually slow through the environment proxy; the parser's local wheel was independently checked against PyPI's published SHA-256. Final image rebuild and browser/role checks are in progress.

## 2026-11-15 — Runtime verification

- User chose to finish local verification and configure live DataHub/LLM connections later.
- Current-source PostgreSQL verification passed reader privileges, direct-write rejection, control/audit isolation, statement timeout, fixture total, and metadata/control availability.
- Headless Chromium passed desktop/mobile query, SQL, trace, clarification, catalog, report, history, and chart flows with no page errors. Inspected both screenshots. Corrected the monetary result header to match its displayed INR units.
- Added bounded upstream streaming and regression handling for incorrect model answers to non-answer evaluation cases. Updated suite: 81 passed, one locally skipped CI PostgreSQL test. Separate actual PostgreSQL checks passed.
- User requested a LaTeX Projects entry with a GitHub link. Added docs/resume-project.tex and docs/RESUME.md using verified claims and an explicit URL placeholder because no Git remote is configured.

## 2026-11-16 — Resume and package handoff preparation

- Latest complete Linux regression suite: 83 passed, including actual PostgreSQL role/timeout checks. One upstream TestClient deprecation warning remains; no test failures.
- The local PostgreSQL backup/restore drill passed: 60 synthetic orders and control schema v1 recovered in a newly created database, which was then removed. The source database was unchanged.
- Desktop/mobile confirmation passed after the INR header fix; no page errors. Pinned Python and PostgreSQL to the tested image digests.
- Docker Desktop stopped during the slow final dependency build. Restarted it and resumed the build while preserving the existing database volumes.
- Updated the resume snippet to the observed 83-test count. No GitHub remote or cloud deployment was created.
- Docker was stopped again at the next continuation. Restarted it and resumed the cached build rather than recreating data. Prepared packaged-runtime checks for source fingerprints, asset hashes, owner-credential absence, non-root execution, and read-only application filesystem.

## 2026-11-16 — Packaged local delivery verified

- Final Docker image built; bootstrap completed idempotently and app/PostgreSQL report healthy. App is bound only to 127.0.0.1:8088.
- Ran the full suite against the installed package without application source mounts: 83 passed, one known TestClient deprecation warning.
- Packaged synthetic evaluation: 18/18 development checks. Real PostgreSQL reader/write rejection, audit isolation, timeout, and reference-metric checks pass against the installed package.
- HTTP smoke checks pass liveness, authentication, readiness, reference query, clarification, catalog, audit history, evaluation report, and browser-asset hash equality.
- Packaged backend source fingerprints match the workspace. Runtime UID is 10001, application filesystem is read-only, and bootstrap credentials are absent. No temporary preview container remains.
- Local project is runnable; live LLM/DataHub, held-out model evaluation, GitHub publication, and cloud deployment remain unperformed as documented. The resume snippet remains marked In Progress with an explicit GitHub URL placeholder.

## 2026-11-16 — Expanded development evaluation

- Added optional 32-scenario suite, independent rowset oracles, citation validation, and per-case timing while preserving the existing six-question default.
- Regression coverage caught a genuine evaluator defect: a matching answer status could remain passed after a later validation failure. Fixed the error handler to fail the case explicitly.
- Expanded scenarios are deliberately labelled development data, including overlapping paraphrases. Live model accuracy remains unmeasured. Verification of this change is in progress.
- The corrected scorer exposed six false passes caused by missing customer context for two segment paraphrases across three seeds. Added bounded, explicit dimension prioritization rather than relaxing evidence validation.
- Rebuilt the package: full Linux/PostgreSQL suite passes 85 tests without source mounts. Expanded development suite passes 96/96; default suite remains 18/18. HTTP smoke checks and all backend/asset fingerprints pass on port 8088.
- Updated the resume entry and verification/status records with these observed counts. No live model calls, GitHub publication, or cloud deployment occurred.

## 2026-11-17 — Trust-engine upgrade

- User requested a substantial upgrade. Prioritized inspectable correctness and DataHub-relevant engineering: column-level value lineage, schema resolution, join-fanout protection, and query-scoped schema impact.
- Added authenticated `/api/inspect` with rate/concurrency bounds and an explicit no-execution contract. Query/evaluation execution paths enforce the commerce semantic guard.
- Added lineage display within the existing SQL view and regression coverage for CTEs, unknown columns, star expansion, impact scopes, raw financial joins, and executor non-invocation.
- Initial local verification: 91 passed, one PostgreSQL test skipped. Packaged/Linux and browser verification are in progress; live connections remain pending.
- Final installed-package verification: 92 tests passed including PostgreSQL and inspection authorization. Both evaluation suites pass (18/18 and 96/96). Desktop/mobile browser checks pass, including the new lineage table; HTTP smoke and asset equality pass.
- App is rebuilt and healthy on port 8088. Updated the resume with actual lineage/impact features and verified counts. No production/live model accuracy claims or public deployment were introduced.

## 2026-11-17 — First paid provider smoke check

- User confirmed the key was added after being told the next step was one small request.
- Sent exactly one synthetic clarification request using the existing Fable/OpenAI-compatible adapter. HTTP 200 was observed; typed Plan validation failed with Pydantic ValidationError.
- Printed no credentials, prompt, SQL, or response text. No database execution or app-mode change occurred. No larger paid evaluation was run, and exact provider charge is unknown.
- Added a redacted one-request checker and documented the unresolved compatibility failure as FABLE-001. Future validation diagnostics expose only standard error types, not rejected inputs.

## 2026-11-17 — Fable provider preparation

- User supplied Fable dashboard/base URL and advertised Claude model labels.
- Checked provider documentation for the OpenAI-compatible `/v1` base, bearer authentication, and exact model IDs.
- Prepared non-secret base/model settings in ignored `.env.docker`, preserving existing key and mode. No credentials were printed and no paid requests were sent.
- Strict JSON-schema/max-completion-token compatibility and live DataHub remain unverified. Added FABLE.md with the exact next steps and limitations.

