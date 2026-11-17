"""One explicitly requested synthetic provider check. Never prints secrets or model text."""

import argparse
import json
import sys

import httpx
from pydantic import ValidationError

from trustsql.catalog import snapshot
from trustsql.config import Settings
from trustsql.errors import TrustSQLError
from trustsql.planner import LLMPlanner


def main():
    parser = argparse.ArgumentParser(
        description="Send one bounded synthetic request; consumes provider credits."
    )
    parser.add_argument("--send", action="store_true", help="Explicitly authorize one provider request")
    args = parser.parse_args()
    if not args.send:
        parser.error("Use --send only when one paid synthetic request has been authorized.")
    statuses = []
    report = {"requests_attempted": 0, "app_mode_changed": False, "warehouse_queries_executed": 0}
    try:
        settings = Settings(_env_file=".env.docker")
        if not settings.llm_api_key.get_secret_value():
            report["error_code"] = "key_missing"
        else:
            report["configured_model"] = settings.llm_model
            client = httpx.Client(
                timeout=settings.llm_timeout_seconds,
                follow_redirects=False,
                event_hooks={"response": [lambda response: statuses.append(response.status_code)]},
            )
            planner = LLMPlanner(settings, client)
            try:
                report["requests_attempted"] = 1
                plan = planner.plan("What was revenue last month?", snapshot()[:4])
                report["valid_typed_plan"] = True
                report["clarification_behavior"] = plan.status == "clarification" and plan.sql is None
                report["passed"] = report["clarification_behavior"]
            finally:
                planner.close()
    except TrustSQLError as exc:
        report["error_code"] = exc.code
        report["upstream_error_type"] = type(exc.__cause__).__name__ if exc.__cause__ else None
        if isinstance(exc.__cause__, ValidationError):
            # Standard validator error codes only; never include rejected input,
            # model text, arbitrary extra-field names, or error context.
            report["validation_error_types"] = sorted(
                {e["type"] for e in exc.__cause__.errors(include_input=False, include_context=False)}
            )
    except Exception as exc:
        report["error_code"] = "configuration_or_client_error"
        report["error_type"] = type(exc).__name__
    report["http_status"] = statuses[-1] if statuses else None
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
