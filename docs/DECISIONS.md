# Decision log

## ADR-012 — Explicit protected-workspace onboarding (2026-11-17, accepted)

Keep the public app shell and authenticated API boundary. A first-visit 401 opens Connection and presents a neutral instruction; a rejected submitted token produces field-local feedback. Tokens remain in tab memory and clear on reload. Do not embed the deployment token in public assets or browser storage. AWS and local tokens remain separate. Verified against the deployed app on desktop and mobile.

Append decisions with context, alternatives, consequences, and verification. Supersede old entries rather than rewriting history.

## ADR-001 — Modular monolith (2026-11-15, accepted)

Use one Python service and same-origin static interface. A separate React service and microservices add deployment overhead without a demonstrated need. Keep internal adapters independent so the boundaries remain testable.

## ADR-002 — Distinct demo and live modes (2026-11-15, accepted)

The deterministic demo provides a runnable credential-free environment. Live mode requires real DataHub metadata and an OpenAI-compatible provider; missing dependencies fail visibly. This prevents fake integration claims while permitting local verification.

## ADR-003 — Independent reader and audit writer (2026-11-15, accepted)

Generated SQL uses a SELECT-only warehouse role. Audit records and durable rate limits use a separate control connection. The offline owner initializes synthetic data but is never used by the application. Parser policy, role privileges, transaction controls, timeouts, and row limits form separate defenses.

## ADR-004 — Explicit commerce semantics (2026-11-15, accepted)

Use cents and an explicit reference date. Net revenue excludes cancelled orders and subtracts successful refunds by the original order date. Aggregate refunds before joining. Ambiguous revenue questions require clarification. This supports checkable answers and meaningful failure cases.

## ADR-005 — Docker deployment (2026-11-15, accepted)

The agreed Python/PostgreSQL architecture requires a container-capable host. Sites hosting runs JavaScript Workers, so it is not the backend deployment target. Prepare Docker Compose and a TLS reverse proxy; select the real hostname/host before publishing.

## ADR-006 — Redacted audit and single-owner access (2026-11-15, accepted)

Store question/SQL hashes, outcome, timings, selected dataset names, and request IDs. Never persist result rows or prompt text by default. Production requires a strong bearer token. This is an owner-operated portfolio app; enterprise SSO and multi-tenant policies are outside the current scope.

## ADR-007 — Reproducible runtime and local port (2026-11-16, accepted)

Pin Python and PostgreSQL to the image digests exercised locally, and cache version-locked dependency wheels in the build stage. This separates dependency downloads from source rebuilds. The host port defaults to 8088 because port 8000 belongs to another local service; the container still listens internally on 8000. No existing service is stopped or reconfigured. Caddy and cloud-specific checks remain pending until a hosting target is selected.

## ADR-008 — Optional expanded development evaluation (2026-11-16, accepted)

Keep the six-question smoke suite as the default, and add an explicit expanded suite with 32 scenarios over eight tasks plus ambiguity/refusal cases. Reuse independent Python oracles and verify rowsets as well as scalars. Validate metadata citations during evaluation. These public, implementation-visible questions remain development data; more paraphrases do not justify a held-out accuracy claim.

## ADR-009 — SQL trust engine (2026-11-17, accepted)

Add schema qualification, SQL-derived column lineage, and a conservative commerce-specific fanout guard before warehouse execution. Reuse the same inspection in evaluation. Expose authenticated, bounded SELECT inspection for query-scoped schema-impact analysis without executing SQL. Display lineage within the existing SQL view. These are deterministic checks, not an LLM confidence score, DataHub lineage readback, or a guarantee of semantic correctness. Retain role isolation, parser policy, and database limits.

## ADR-010 — Prepare user-selected Fable provider (2026-11-17, pending live verification)

User supplied Fable's API base and model labels. Configure its documented OpenAI-compatible base `https://api.fableaiapi.com/v1` and advertised `claude-sonnet-5-5` identifier in ignored local settings. Preserve the key and app mode. Do not infer strict JSON-schema support from a generic compatibility claim. No paid calls or production/live claims until the request contract is verified. See FABLE.md.

## ADR-011 — Public repository and low-cost serverless edition (2026-11-17)

User explicitly authorized GitHub public publication and AWS deployment, then capped the target cost below US$5/month and reported no domain. Prepare a Lambda Function URL with a synthetic SQLite warehouse and persistent DynamoDB audit/rate limits; preserve PostgreSQL in the full Docker edition. No provider key is sent to cloud. Proceed with chargeable resource creation only after clarifying that usage-based costs have no strict cap. See AWS.md for scope and limitations.

