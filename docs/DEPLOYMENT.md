# Deployment and operations

## Local development

Use the README commands. SQLite is credential-free development only. Runtime data is in ignored `var/`. Seeding is explicit and does not overwrite existing data.

## PostgreSQL containers

1. Start Docker Desktop/the Docker daemon.
2. Run `python -m trustsql.cli init-docker-env` once; it creates unique hex passwords and an owner token in ignored `.env.docker`. Existing files are never overwritten.
3. Run `docker compose --env-file .env.docker config --quiet` to validate without printing resolved secrets.
4. Run `docker compose --env-file .env.docker up --build -d`.
5. Check `docker compose --env-file .env.docker ps`. The one-shot bootstrap must exit successfully and the app must become healthy.
6. Open `http://127.0.0.1:8088` (or the configured `TRUSTSQL_PORT`) and enter its generated API token. Check the catalog and execute a supported example.

The PostgreSQL volume is durable. Initialization SQL runs only for a new volume. Changing a password in the env file does not rotate an existing database role: rotate in PostgreSQL deliberately, then update the matching secret. `docker compose down` stops the stack; do not add `-v` unless you explicitly intend to erase the warehouse and audit history.

## Production

Choose a container-capable host and a hostname. Configure DNS and allow ports 80/443. Create an ignored `.env.production` from the Docker configuration and set:

- `TRUSTSQL_MODE=live`, `TRUSTSQL_ENVIRONMENT=production`.
- `TRUSTSQL_DOMAIN` to the hostname, without a scheme.
- Strong unique passwords and an API bearer token of at least 32 characters.
- A valid model key/model/base URL; the provider must support the structured Chat Completions schema used by the adapter.
- A DataHub token and HTTPS GraphQL endpoint. Publish/read back the approved synthetic metadata first.

```text
docker compose --env-file .env.production -f compose.yml -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.yml -f compose.production.yml up --build -d
```

Caddy obtains a TLS certificate for the selected domain. The app stays on a loopback-bound local port; PostgreSQL has no public port. Production startup rejects SQLite, missing tokens, demo mode, wildcard hostnames, and non-HTTPS upstreams. The runtime container is non-root with a read-only filesystem and a writable report volume. This is single-owner access, not tenant isolation or SSO.

Before launch, complete ACCEPTANCE.md, scan dependencies/images in the chosen CI environment, and configure external uptime monitoring. Python and PostgreSQL are pinned to the locally tested immutable image digests. Pin the optional Caddy image after testing the selected TLS deployment. No cloud deployment is claimed before these checks are recorded.

## Health and logs

`/health/live` is public process liveness. `/health/ready` requires the API token and checks warehouse tables/reader privileges, control schema, and metadata. The container health script reads the token from its environment and never prints it. Logs are JSON events with request ID, status, and duration; they exclude question text, SQL, result rows, and credentials. Match UI request IDs against audit records when investigating.

## Evaluation reports

Local: `python -m trustsql.cli evaluate`.

Container: `docker compose --env-file .env.docker exec app python -m trustsql.cli evaluate`.

Live experiments: run with live settings and separate outputs for `--variant metadata` and `--variant schema_only`. Both variants retrieve the same candidate datasets; the schema-only variant removes descriptions and context signals before generation. This isolates the generation-context comparison, not retrieval quality. Initial cases are development cases and must not be called held out. Model cost is incurred only for explicit live runs. There is no public endpoint that launches a paid benchmark.

## Backup and recovery

Use a scheduled PostgreSQL custom-format `pg_dump` through the database container to a restricted backup destination. Back up Caddy state if relying on that instance's certificate storage. Encrypt backups, set retention, and test `pg_restore` into a disposable database before launch. Audit records contain hashes rather than raw prompts/results; retaining a backup still requires access control. The local synthetic-fixture restore drill passed using `infra/postgres/verify-backup.sh`. Scheduled, encrypted off-host backups and a restore drill on the selected deployment host remain pending.

## Rollback

Retain the previous tested image digest. Stop new query traffic, restore the prior compatible image, and verify readiness. Initial control schema version is 1; future schema changes require an explicit migration and compatibility decision. Never run destructive resets as an automatic startup or rollback step.

