from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.scope import traverse_scope

from trustsql.errors import TrustSQLError

TABLES = frozenset({"customers", "products", "orders", "order_items", "payments", "refunds"})
FUNCTIONS = frozenset(
    {
        "SUM",
        "COUNT",
        "AVG",
        "MIN",
        "MAX",
        "COALESCE",
        "NULLIF",
        "ROUND",
        "ABS",
        "LOWER",
        "UPPER",
        "LENGTH",
        "DATE_TRUNC",
        "EXTRACT",
        "CAST",
        "TRY_CAST",
        "SUBSTRING",
        "CONCAT",
        "DATE",
        "STRFTIME",
        "TIME_TO_STR",
        "TS_OR_DS_TO_DATE",
        "CURRENT_DATE",
    }
)


@dataclass(frozen=True)
class ApprovedQuery:
    sql: str
    tables: tuple[str, ...]


def validate_sql(sql: str, dialect: str = "postgres") -> ApprovedQuery:
    def reject(message="Only a single read-only query over the approved analytics tables is allowed."):
        raise TrustSQLError("sql_rejected", message, 422)

    if not sql or len(sql) > 12000 or sql.count("(") > 128:
        reject()
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except (SqlglotError, ValueError, RecursionError) as exc:
        raise TrustSQLError("sql_rejected", "The generated SQL could not be parsed safely.", 422) from exc
    if len(statements) != 1 or statements[0] is None:
        reject()
    tree = statements[0]
    if sum(1 for _ in tree.walk()) > 2000:
        reject("The query exceeds the supported complexity limit.")
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        reject()
    forbidden = (
        exp.DDL,
        exp.DML,
        exp.Command,
        exp.Into,
        exp.Lock,
        exp.Transaction,
        exp.Set,
        exp.Use,
        exp.Grant,
        exp.Revoke,
    )
    if any(isinstance(node, forbidden) for node in tree.walk()):
        reject()
    if any(node.args.get("recursive") for node in tree.find_all(exp.With)):
        reject("Recursive queries are outside the allowed query policy.")
    if len(list(tree.find_all(exp.CTE))) > 8:
        reject()
    for node in tree.find_all(exp.Func):
        # SQLGlot models Boolean connectives as Func subclasses too. They are
        # language operators, not calls to database functions.
        if isinstance(node, (exp.And, exp.Or)):
            continue
        name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name().upper()
        if name not in FUNCTIONS:
            reject("The query uses a function that is outside the approved analytics policy.")
    # LATERAL/UDTF and table functions are excluded even if a function itself is allowed.
    if tree.find(exp.Lateral) or tree.find(exp.Unnest):
        reject()
    if any(dot.find(exp.Func) for dot in tree.find_all(exp.Dot)):
        reject("Schema-qualified functions are outside the approved analytics policy.")
    used = set()
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                if (
                    not isinstance(source.this, exp.Identifier)
                    or source.catalog
                    or source.db not in ("", "analytics")
                    or source.name not in TABLES
                ):
                    reject("The query references a table or schema outside the approved catalog.")
                used.add(source.name)
    if not used:
        reject("The query must use an approved analytics table.")
    # Qualifiers are normalized for the warehouse implementation, never taken from user configuration.
    return ApprovedQuery(tree.sql(dialect=dialect), tuple(sorted(used)))
