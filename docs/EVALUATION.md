# Evaluation guide

The default `development` suite is six questions across three fixture seeds (18 checks). It remains the quick smoke report shown in the application.

The optional `expanded` suite is 32 question scenarios across three seeds (96 checks). It covers eight underlying analytics tasks with three paraphrases each, four ambiguous-revenue questions, and four refusal requests. The scenarios overlap semantically; 32 scenarios do not represent 32 independent tasks.

```powershell
python -m trustsql.cli evaluate --suite expanded --output var/evaluation-expanded.json
```

Inside Docker:

```text
docker compose --env-file .env.docker exec -T app python -m trustsql.cli evaluate --suite expanded --output var/evaluation-expanded.json
```

Scalar answers are checked against independent Python calculations. Product rankings, segment sales, and regional customer counts are checked as complete ordered rowsets. All calculations are repeated over seeds 7, 19, and 42. Metadata citations and the SQL policy are enforced before execution. Any validation/execution error fails the case even if the planner selected the expected answer status. Per-case duration is recorded, including failed cases.

All scenarios are explicitly development data. They have been used while implementing the project and must not be relabelled held out. Deterministic demo passes test the fixture pipeline and rule-based planner, not an LLM. Live model experiments require user-configured connections and explicit live execution; none have been run.

The evaluator uses SQLite fixtures after transpiling live PostgreSQL SQL, so it measures fixture result behavior rather than general PostgreSQL equivalence. Model cost/token usage, genuine held-out cases, and broader dialect behavior remain future work. The reported duration covers retrieval, planning, validation, and execution; it is not a server throughput benchmark.
