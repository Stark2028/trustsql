# Bug register

Use stable IDs. Record reproduction, expected/actual behavior, severity, resolution, and regression evidence. Open issues remain visible in STATUS.md.

| ID | Severity | State | Description | Evidence / resolution |
|---|---|---|---|---|
| ENV-001 | Environment | Resolved for current run | Docker Linux engine stopped between work sessions | Restarted; final packaged stack is healthy on port 8088 and data was preserved; Docker must remain running to use the local app |
| ENV-002 | Tooling | Documented | Impeccable engine cannot initialize external cache | Used skill fallback; does not block application implementation |
| SQL-001 | Medium | Fixed | Qualifying every table-shaped AST node can accidentally qualify a CTE that shadows a physical table name | Qualify only physical sources from SQLGlot scopes; regression in test_pipeline.py |
| ENV-003 | Environment | Mitigated | PyPI CDN downloads repeatedly time out, including outside the sandbox | Final build completed using cached version-locked wheels, longer timeout, and build-layer separation |
| SQL-002 | Medium | Fixed | SQLite optimized COUNT(*) reports a read with no database name, so an overly strict authorizer rejects legitimate counts | Confirmed via native sqlite3 callback inspection; allow the documented empty-database case for approved tables only |
| SQL-003 | Medium | Fixed | PostgreSQL SUM(bigint) returns Decimal; serializing all Decimals as strings changes an integer-money result's type | Preserve integral Decimals as exact integers; fractional values remain strings; regression in test_pipeline.py |
| SQL-004 | High | Fixed | SQLGlot represents AND/OR as Func subclasses, so the function allowlist rejected ordinary filtered analytics | Concrete Boolean operator AST types permitted; full local suite and PostgreSQL query check pass |
| ENV-004 | Environment | Resolved | Local port 8000 belongs to another service | Docker host port defaults to configurable 8088; existing service left untouched |
| EVAL-001 | Medium | Fixed | A model answering a refusal/clarification case tried to access a missing metric oracle and could crash evaluation | Wrong status is recorded as a failed case; regression test preserves the complete report |
| NET-001 | Medium | Fixed | Checking response size after a full upstream read did not bound memory consumption | Streamed metadata/model reads stop at the byte limit; regression test checks early termination |
| UI-001 | Low | Fixed | Result cells displayed INR while the header still said cents | Display headers now say INR; browser confirmation passes and SQL column names remain inspectable |
| EVAL-002 | High | Fixed | Evaluation could leave passed=true after a matching answer status followed by validation/execution failure | Success flag cleared on error; regression passes against the installed package |
| RET-001 | Medium | Fixed | Revenue-heavy lexical matches excluded customers for segment paraphrases | Explicit dimension prioritization preserves the bounded retrieval; expanded 96/96 checks and full package suite pass |
| SEM-001 | High | Fixed | Read-only valid SQL could aggregate raw order items after joining multiple refunds/payments, inflating totals | Guard rejection and safe CTE pre-aggregation pass installed-package regression tests |
| FABLE-001 | Integration | Open | First real Fable request returns HTTP 200 but its content fails typed Plan validation | One request sent with configured key; no raw output retained, SQL execution, or mode change; response-format compatibility still needs diagnosis |
| UI-002 | Medium | Fixed | A fresh protected homepage displayed an authentication error before the visitor entered a token; Connection remained collapsed | Initial HTTP 401 now opens Connection with a neutral prompt. Invalid tokens get field-local feedback. Hosted desktop/mobile browser checks cover missing, invalid, valid, and reload states; API authentication remains enforced |

