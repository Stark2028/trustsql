# Learnings

## Metadata is part of answer correctness

A query can execute successfully while counting the wrong business quantity. Schema names do not tell an agent whether revenue excludes cancellations or includes refunds. Store and retrieve explicit definitions, then evaluate actual result values.

## Multiple one-to-many joins can inflate money

Joining order items, payments, and refunds directly creates repeated rows. Aggregate each source at the intended grain before joining. A plausible total is not sufficient evidence; fixtures should deliberately contain multiple payments/refunds.

## Read-only is a database property too

Checking for the word SELECT is inadequate: CTE mutations, external functions, system catalogs, and resource exhaustion need separate controls. Validate the AST and limit privileges, runtime, and returned rows.

## Production readiness needs observations

A Dockerfile is a deployment artifact, not proof that an image boots. Adapter unit tests are not a live DataHub/LLM test. Track these separately so reviewers can see what has actually been checked.

## SQL AST scopes differ from surface table names

A CTE named `orders` may shadow a physical table with that name. Qualifying every table-shaped node with a database schema changes the meaning of a valid query. Resolve scopes and qualify only physical sources.

## Database callbacks have special cases

SQLite reports `COUNT(*)` as a table read with an empty column and no database name. An authorizer that requires `database == 'main'` for all reads rejects legitimate counts. Verify callback behavior directly and keep the table allowlist in place.

## Bound network reads before decoding

Checking a response size after `response.json()` has already consumed memory does not bound the network read. Stream the response, count bytes, stop at the cap, and validate its JSON shape before handing it to the adapter.

## Keep evaluation failures inside the report

A model can produce executable SQL when the expected behavior is refusal or clarification. Such a case has no numeric oracle. Record the incorrect status as a failed case, rather than indexing a missing reference and crashing the whole run.

## A failed validation must override an initially correct status

Setting passed=true immediately after a planner returns an answer is premature. Later citation, policy, or execution failures must clear that flag. Fixing this scorer exposed real retrieval errors that a superficially perfect pass rate had hidden.

## Retrieval must preserve the requested dimension

Revenue descriptions can dominate lexical scores and crowd out a customer dimension needed for segment analysis. Prioritize explicitly named dimensions inside the bounded result set and validate that every queried table was retrieved and cited. Do not bypass evidence validation to improve a score.

## Value lineage and row selection answer different questions

A net-revenue value comes from quantities, prices, and refund amounts, while order dates/status and join keys determine which rows contribute. Report value origins and all query dependencies separately. Neither should be described as a complete warehouse-wide lineage graph.

