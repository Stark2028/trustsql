# Security model

Assets: provider tokens, warehouse records, metadata, audit integrity, model-call budget, and service availability.

Boundaries: browser to API; API to metadata; untrusted model output to policy; policy to warehouse; app to audit store. Both question text and metadata can contain prompt injection. No prompt is a security boundary.

Controls: production bearer token; same-origin UI; no permissive CORS; trusted Host validation; strict request bounds; atomic database rate limiting; bounded concurrency; typed planner output; SQL relation/function allowlists; read-only role/transactions; query timeout; result cap; redacted structured logs; durable audit trail; non-root container; separate bootstrap credentials.

The static app shell and liveness endpoint can be public. Catalog, queries, readiness, run history, and benchmark summaries require API authentication when configured. Browser tokens remain in memory and are cleared on reload. Use a TLS reverse proxy for production. Do not expose this owner-token architecture as a multi-tenant service.

Residual risks: metadata can be wrong; models can return semantically incorrect SQL; read queries can consume resources before their timeout; rows returned to an authorized owner can contain allowed warehouse data. This first release uses synthetic data and curated tables. Live metadata transport and providers must use HTTPS in production. Deploy trusted origins only; do not use a public untrusted proxy for credentials.

Security reports: open a private report to the repository owner once a repository is published. Do not put credentials or real records in public issues.

