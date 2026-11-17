# TrustSQL

A metadata-aware SQL analyst with inspectable evidence, constrained execution, and reproducible evaluation. Built as a DataHub-relevant AI engineering portfolio project.

The SQL trust engine resolves column schemas, traces value origins through CTEs, blocks a known financial join-fanout pattern, and exposes query-scoped schema-impact inspection without execution. See [Trust engine](docs/TRUST_ENGINE.md) for an API example and limitations.

**Current verification and outstanding checks: [docs/STATUS.md](docs/STATUS.md).** Demo mode is deterministic and uses synthetic data; it does not call an LLM or DataHub. Live mode connects to both and fails visibly if either connection is unavailable.

## Run locally

Python 3.12 is required. From the repository root, on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m trustsql.cli seed
.\.venv\Scripts\python.exe -m trustsql.cli evaluate
.\.venv\Scripts\python.exe -m uvicorn trustsql.app:app --host 127.0.0.1 --port 8088 --no-access-log
```

On macOS/Linux, use `.venv/bin/python` in place of the Windows Python path. Open <http://127.0.0.1:8088>. No keys are needed for this explicitly labelled demo. Choose another port if you already have the Docker version running. Do not expose the unauthenticated development server publicly.

Try `What was our net revenue last month?`, then inspect SQL, execution trace, and metadata. Ask `What was revenue last month?` to see clarification. The fixture reference date is **2026-11-15**, so last month means October 2026.

## Container deployment

```powershell
.\.venv\Scripts\python.exe -m trustsql.cli init-docker-env
docker compose --env-file .env.docker up --build -d
```

Open <http://127.0.0.1:8088> and enter the generated `TRUSTSQL_API_TOKEN` from `.env.docker` in Connection. Set `TRUSTSQL_PORT` to change this host port. Do not paste secrets into logs or screenshots. This stack runs the deterministic demo over PostgreSQL with separate reader/control roles. It does not pretend to be a live model.

For live configuration, TLS, deployment checks, and operations, use [DEPLOYMENT.md](docs/DEPLOYMENT.md) and [DATAHUB.md](docs/DATAHUB.md).

## Checks

```powershell
.\.venv\Scripts\python.exe -m pip install pytest==9.1.1
.\.venv\Scripts\python.exe -m pytest -q --basetemp scratch/pytest
.\.venv\Scripts\python.exe -m trustsql.cli evaluate
```

The default benchmark is six **development questions**, checked across three seeds (18 checks) using an independent Python oracle. An optional expanded suite covers 32 development scenarios across three seeds (96 checks), including ordered product/segment/region result tables. These scenarios include paraphrases and are neither held-out model accuracy nor proof of production reliability.

```text
python -m trustsql.cli evaluate --suite expanded --output var/evaluation-expanded.json
```

See [Evaluation guide](docs/EVALUATION.md) for scope and limitations. Live model experiments and a genuinely held-out suite remain pending.

## Project records

| File | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Components, trust boundaries, query lifecycle, data semantics |
| [Decisions](docs/DECISIONS.md) | Alternatives and architectural reasoning |
| [Work log](docs/WORKLOG.md) | Session-by-session changes and verification |
| [Bugs](docs/BUGS.md) | Stable IDs, reproductions, fixes, and regressions |
| [Learnings](docs/LEARNINGS.md) | Concepts and explanations for interview preparation |
| [Status](docs/STATUS.md) | Implemented vs verified vs pending |
| [Release acceptance](docs/ACCEPTANCE.md) | Evidence required before a production claim |
| [Verification record](docs/VERIFICATION.md) | Observed check results and reproduction notes |
| [Resume entry](docs/resume-project.tex) | LaTeX project entry with an explicit GitHub URL placeholder |
| [Security](docs/SECURITY.md) | Threat model, controls, and residual risks |
| [Roadmap](docs/ROADMAP.md) | Prioritized remaining work |

