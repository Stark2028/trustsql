# Delivery status

Last updated: 2026-11-17. Evidence, not intent, determines status.

| Area | Status | Evidence / next check |
|---|---|---|
| Architecture and project records | Created | ARCHITECTURE.md, DECISIONS.md, PRODUCT.md |
| Analyst interface | Implemented; browser checked | Desktop 1440px/mobile 390px, no JS errors or horizontal overflow; all main flows pass against PostgreSQL-backed preview |
| SQL execution and policy | Implemented; regression checked | 92 tests pass in Linux including PostgreSQL, lineage, impact, and semantic-guard regressions |
| Synthetic commerce data | Verified | Independent Python oracle matches net/gross/refund/count SQL across three seeds |
| DataHub integration | Implemented; contract checked | Real endpoint/ingestion readback pending; user will configure later |
| LLM connection | First live request attempted; not working yet | One Fable request returned HTTP 200 but failed typed-plan validation; DataHub/app live mode still pending |
| Fable provider settings | Key configured; compatibility unresolved | Correct `/v1` base and provider model ID configured; response was not a valid Plan; app remains demo |
| Offline evaluation | Working | Default 18/18 and expanded 96/96 development checks (32 scenarios × 3 seeds); explicitly not LLM accuracy |
| PostgreSQL runtime | Role/execution checks pass | Latest-source preview: direct writes rejected, audit inaccessible, timeout enforced, net revenue matches oracle |
| Packaged container | Rebuilt and verified locally | Healthy at http://127.0.0.1:8088; 92 tests pass against the installed wheel without source mounts |
| SQL trust engine | Implemented and verified | CTE value lineage in SQL view; schema validation; financial join-grain guard; authenticated no-execution impact inspection |
| Cloud deployment | Not deployed | Hostname/hosting account not selected |
| Local backup/restore | Verified | pg_dump/pg_restore drill recovered all 60 synthetic orders and control schema v1 in a temporary database |

TrustSQL and PostgreSQL are running locally; open http://127.0.0.1:8088 and enter `TRUSTSQL_API_TOKEN` from ignored `.env.docker` in Connection. Browser checks passed on desktop/mobile; the final packaged app serves identical asset hashes. Its HTTP checks pass liveness, authentication, readiness, reference totals, clarification, catalog, audit, and evaluation report. The app runs as UID 10001 with a read-only application filesystem and no bootstrap credentials. The temporary preview container is gone. Browser evidence is in ignored `artifacts/browser/` and runtime fingerprints are in ignored `artifacts/runtime-fingerprint.json`.

Do not describe this release as production-verified until the acceptance checklist passes. Do not claim an accuracy improvement without a held-out live benchmark.

