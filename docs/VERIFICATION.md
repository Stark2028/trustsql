# Verification record

Last updated: 2026-11-17. This is a human-readable record of observed checks, not a claim that pending integrations have been exercised.

| Check | Observed result | Scope |
|---|---|---|
| Complete Python suite in Linux | 92 passed | Rebuilt installed package, no application source mounts, locked dependencies, real PostgreSQL role test included |
| Trust engine | Pass | CTE lineage, unknown columns, star expansion, raw financial join rejection, schema impact, API auth, and executor non-invocation |
| SQL policy | Pass | Mutations, multi-statements, recursive CTEs, catalogs, external functions, schema-qualified functions, locking, and CTE shadowing |
| API controls | Pass | Authentication, body/request bounds, Host validation, rate limiting, audit redaction, unavailable-store handling |
| Upstream adapters | Pass | Mocked HTTP contract, malformed responses, byte caps, no silent DataHub fallback |
| Independent oracle | Pass | Net/gross/refund/order-count answers across seeds 7, 19, 42 |
| Development evaluation | 18/18 | Deterministic fixture checks, explicitly not model accuracy |
| Expanded development evaluation | 96/96 | 32 scenarios × 3 seeds, ordered rowsets and scalars; paraphrases across eight tasks, not held out |
| PostgreSQL runtime | Pass | Reader refuses writes/audit reads; timeout SQLSTATE 57014; reference net revenue matches |
| Browser | Pass | Desktop 1440×1000 and mobile 390×844; query, SQL, trace, clarification, catalog, evaluation, history, chart; no page errors |
| Backup/restore | Pass | Temporary restored database recovered 60 synthetic orders and control schema v1; source preserved |
| Python/JS checks | Pass | Ruff checks and formatting, Python compilation, Node syntax check |
| Initial image/bootstrap | Pass | Initial package image built; PostgreSQL initialization succeeded |
| Final corrected package image | Pass | Healthy local Compose app on 8088; packaged module/asset hashes match workspace, no source mounts |
| Runtime hardening | Pass | UID 10001, read-only application filesystem, bootstrap credentials absent |
| Packaged HTTP smoke checks | Pass | Liveness, authentication, readiness, reference query, clarification, catalog, audit history, report, asset hashes |
| Live DataHub and model | Pending by user choice | Credentials/endpoints to be configured later |
| GitHub CI and cloud hosting | Not run | No remote configured; no site published |

One TestClient deprecation warning from the installed Starlette/httpx combination remains. The suite passes; no model-accuracy, uptime, or production-readiness percentage is inferred from these checks.

The final Docker runtime installs the built TrustSQL wheel and its dependencies from the build-stage wheel directory using `--no-index`, without fetching from a package index during that install. Python/PostgreSQL images and runtime package versions are pinned. The optional TLS proxy, live integrations, dependency/image security scan, and host-specific operations still require release checks.

## Reproduction

Use README.md for setup. Run `python -m pytest -q` with a disposable PostgreSQL instance and `TRUSTSQL_TEST_POSTGRES_URL` to include the PostgreSQL test; optional reader/control test URL variables support non-CI credentials. Never paste credentials into logs.

`scripts/verify_postgres.py` uses the app's configured reader/control connections for non-destructive database checks. `scripts/browser_smoke.py` reads the owner token from ignored `.env.docker` and supports `TRUSTSQL_SMOKE_BASE_URL` for a local preview. Screenshots are ignored artifacts under `artifacts/browser/`.

`infra/postgres/verify-backup.sh` is a local synthetic-fixture drill using the offline owner. It creates a temporary restore database and removes only that newly created database after verification. It is not a scheduled or off-host backup service.
