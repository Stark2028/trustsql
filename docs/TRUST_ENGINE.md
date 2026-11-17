# SQL trust engine

Implemented 2026-11-17. The engine combines existing SQL policy and database controls with schema resolution, value lineage, and conservative commerce-specific join checks. It does not establish general business correctness.

## Demonstration

Ask for net revenue last month, then open SQL query. The output's sources include `order_items.quantity`, `order_items.unit_price_cents`, and `refunds.amount_cents`, traced through the aggregation CTEs. Query dependencies separately include date/status filters and join keys.

Authenticated `POST /api/inspect` accepts a SELECT for analysis only:

```json
{
  "sql": "SELECT SUM(amount_cents) AS total FROM refunds WHERE status = 'succeeded'",
  "changed_table": "refunds",
  "changed_column": "amount_cents"
}
```

The response includes `executed: false`, output-to-source column mappings, all referenced query columns, join-risk findings, and an optional impact report. Removing or changing `refunds.amount_cents` affects output `total`; changing a filter-only field is reported separately as a row-selection/join dependency. This endpoint shares authentication, rate limiting, and concurrency limits with query execution. It never calls the warehouse executor or the LLM and does not persist raw SQL.

Inspection applies to the submitted SELECT, not to every dashboard in a warehouse. Source provenance is `sql_derived`, not a claim that the result was read from DataHub's lineage graph.

## Semantic guard

Raw order items joined to raw payments/refunds in the same aggregate scope can multiply monetary values. The guard blocks these SUM queries before execution and records a redacted error. Aggregating the sources separately before joining, as in the net-revenue demo, passes. Unknown columns fail schema resolution before execution.

The rule is conservative and tied to this synthetic commerce contract. It may reject carefully constructed safe queries, and it cannot detect all incorrect calculations. It is not a calibrated confidence score. Value lineage does not describe every indirect effect of row selection; the separate dependency set captures referenced filter/join columns.

The implementation uses the installed SQLGlot lineage and qualification APIs, checked against [official API documentation](https://sqlglot.com/sqlglot/lineage.html). It returns structured JSON and renders plain text nodes; it does not embed generated SQLGlot HTML.
