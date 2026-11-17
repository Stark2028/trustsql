# Low-cost AWS demo

User requested a public GitHub repository, AWS hosting, a budget below US$5/month, and no custom domain (2026-11-17).

The proposed cloud edition uses Lambda Python 3.12 with a managed HTTPS Function URL, SQLite synthetic warehouse fixtures, and durable DynamoDB audit/rate-limit storage. The full Docker edition retains PostgreSQL role isolation and its integration tests. The serverless edition is explicitly a deterministic demo, not a deployment of live DataHub/Fable or a claim to run PostgreSQL on Lambda.

There is no always-on VM, RDS, NAT gateway, load balancer, or custom domain charge. Charges are usage-based; under US$5 is a low-traffic estimate, not a guaranteed cap. User explicitly accepted that risk before resource creation. Account concurrency quota is 10, so an unsupported reserved allocation was omitted. Execution timeout is 15 seconds, logs expire after 7 days, rate counters expire after minutes, and audit records expire after 7 days. An account-wide US$4 budget monitor was created; it has no automatic shutdown or email notification. Student-credit applicability is account-specific.

API routes require a fresh, deployment-specific bearer token saved locally in ignored `var/aws/api.env`. The frontend shell is publicly readable. No Fable key, local database password, or AWS credential is bundled or copied to GitHub/Lambda. The execution role accesses only its DynamoDB table and log group.

The handler seeds only synthetic data during cold start and uses SQLite read-only execution controls. DynamoDB provides durable redacted audit records and atomic rate limits across instances. Do not use this edition for real customer data or advertise it as the full production/PostgreSQL deployment.

Deployment files: `infra/aws/template.json`, `infra/aws/lambda_handler.py`, `infra/aws/Dockerfile`, and `infra/aws/deploy.py`. The template is validated with CloudFormation before deployment. The code artifact bucket blocks public access. DynamoDB is retained on stack deletion to prevent accidental audit deletion; review/delete retained resources explicitly when decommissioning. The artifact bucket is separate and also requires deliberate cleanup.

Live deployment status and URLs are recorded in STATUS.md only after actual health/query checks. GitHub publication requires a staged-content scan against local secret values and known token patterns.

## Verified deployment — 2026-11-17

CloudFormation stack `trustsql-demo` in `ap-south-1` reached CREATE_COMPLETE. HTTPS app: https://dkvojj4i5rz4pcaawu2qdrhh4e0mhjaz.lambda-url.ap-south-1.on.aws/ . Frontend, authentication, readiness, reference net-revenue query, and durable DynamoDB history checks pass. The function has no provider key.

`finalize.py` sets the exact generated hostname after initial creation and performs the checks. This changes the initial localhost host setting; rerun finalization after stack updates. The deploy helper currently creates a new stack and is not yet an idempotent update manager.
