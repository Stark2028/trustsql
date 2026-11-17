# DataHub connection

Live DataHub verification requires a running DataHub instance and an access token. Use a separate ingestion environment if the SDK has dependencies incompatible with the app's locked environment.

1. Run the warehouse fixture in PostgreSQL. Its database name must be `trustsql` and schema `analytics` for the approved dataset URNs.
2. In a separate Python environment, install `acryl-datahub[postgres]` and this project. Supply `DATAHUB_GMS_URL`, `TRUSTSQL_DATAHUB_TOKEN`, `POSTGRES_HOST_PORT`, and `TRUSTSQL_READER_PASSWORD` locally.
3. Run `datahub ingest -c ingestion/postgres.yml` for actual warehouse schema discovery. The connector is read-only and profiling is disabled.
4. Run `python scripts/publish_metadata.py` to publish the synthetic dataset descriptions, metric definitions, and schema into DataHub. It emits metadata through the official SDK. No row values are uploaded.
5. Set `TRUSTSQL_MODE=live`, a valid LLM key, and `TRUSTSQL_DATAHUB_GRAPHQL_URL` (the full GraphQL endpoint). The app reads all six approved datasets, validates the schema against the catalog contract, caches briefly, and retrieves a relevant subset for each question.
6. Verify `/health/ready`, the catalog's `source=datahub`, and a query with real metadata evidence. Record the DataHub version and ingestion/readback result in STATUS.md.

The app uses dataset descriptions as its business-definition context. Dedicated glossary entity management and column-level lineage are later features. `trustsql.certified` and `trustsql.freshness` are explicit synthetic custom properties; they are not a claim to implement DataHub's production certification or quality-monitoring system.

GraphQL contract tests use mocked HTTP responses. They do not replace step 6. Live errors never trigger a silent fallback to the fixture snapshot.

