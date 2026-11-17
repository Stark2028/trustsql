"""SQL-derived evidence, not warehouse/DataHub lineage or proof of semantic correctness."""

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.lineage import lineage
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope

from trustsql.errors import TrustSQLError
from trustsql.models import Dataset
from trustsql.policy import ApprovedQuery


def inspect_query(approved: ApprovedQuery, datasets: list[Dataset], dialect="postgres") -> dict:
    tree = sqlglot.parse_one(approved.sql, read=dialect)
    risks = []
    for scope in traverse_scope(tree):
        physical = {s.name for s in scope.sources.values() if isinstance(s, exp.Table)}
        # All three are one-to-many at the order grain. Joining raw rows before
        # aggregation can repeat monetary amounts. This conservative rule is
        # deliberately limited to the project's curated commerce contract.
        if (
            "order_items" in physical
            and physical & {"payments", "refunds"}
            and any(isinstance(n, exp.Sum) for n in scope.expression.walk())
        ):
            risks.append(
                {
                    "code": "join_fanout",
                    "severity": "blocking",
                    "tables": sorted(physical),
                    "message": "Raw order lines are joined with multiple payment/refund rows before SUM. Aggregate each source to the order grain before joining.",
                }
            )
    schema = {d.table: {c.name: c.type for c in d.columns} for d in datasets}
    # Use one normalized schema level for both qualified/unqualified fixture SQL.
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                source.set("db", None)
    try:
        qualified = qualify(
            tree, dialect=dialect, schema=schema, identify=False, validate_qualify_columns=True
        )
        dependencies = set()
        for scope in traverse_scope(qualified):
            for column in scope.columns:
                source = scope.sources.get(column.table)
                if isinstance(source, exp.Table):
                    dependencies.add(f"{source.name}.{column.name}")
        outputs = []
        for name, root in lineage(None, qualified, schema=schema, dialect=dialect).items():
            origins = set()
            unresolved = False
            for node in root.walk():
                if node.downstream:
                    continue
                if isinstance(node.expression, exp.Table):
                    column = node.name.rsplit(".", 1)[-1].strip('"')
                    origins.add(f"{node.expression.name}.{column}")
                elif isinstance(node.expression, exp.Placeholder):
                    unresolved = True
            outputs.append({"output": name, "sources": sorted(origins), "resolved": not unresolved})
    except (SqlglotError, ValueError, KeyError, TypeError) as exc:
        raise TrustSQLError(
            "schema_validation_failed",
            "The query could not be resolved against the approved column schema. No query was executed.",
            422,
        ) from exc
    return {
        "provenance": "sql_derived",
        "tables": list(approved.tables),
        "columns": outputs,
        "query_dependencies": sorted(dependencies),
        "risks": risks,
        "limitations": [
            "Value lineage excludes indirect row-selection effects; query_dependencies includes filter and join columns.",
            "Fanout checks are conservative rules for this commerce schema, not a general proof of correctness.",
        ],
    }


def enforce_semantics(report: dict):
    if any(r["severity"] == "blocking" for r in report["risks"]):
        raise TrustSQLError(
            "semantic_risk",
            "The query may inflate monetary totals by joining multiple one-to-many sources. Aggregate each source before joining; no query was executed.",
            422,
        )


def change_impact(report: dict, table: str, column: str | None = None) -> dict:
    target = f"{table}.{column}" if column else table
    affected = [
        item["output"]
        for item in report["columns"]
        if any(source == target if column else source.startswith(table + ".") for source in item["sources"])
    ]
    dependency = target in report["query_dependencies"] if column else table in report["tables"]
    return {
        "target": target,
        "referenced_by_query": dependency,
        "affected_outputs": affected,
        "row_selection_or_join_dependency": dependency and not affected,
        "provenance": "sql_derived",
        "scope": "This submitted SELECT only; not an estate-wide dependency graph.",
    }
