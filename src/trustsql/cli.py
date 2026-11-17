import argparse
import json
import os
import secrets
from pathlib import Path

from trustsql.config import Settings
from trustsql.control import ControlStore
from trustsql.db import make_engine
from trustsql.seed import seed_warehouse


def main():
    parser = argparse.ArgumentParser(description="TrustSQL administration; no secrets are printed.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="Initialize local demo data and audit schema")
    commands.add_parser(
        "bootstrap",
        help="Initialize PostgreSQL synthetic fixture and control schema using offline owner credentials",
    )
    evaluate = commands.add_parser("evaluate", help="Run the development fixture benchmark")
    evaluate.add_argument("--variant", choices=["metadata", "schema_only"], default="metadata")
    evaluate.add_argument("--output", default="var/benchmark-summary.json")
    evaluate.add_argument("--suite", choices=["development", "expanded"], default="development")
    env = commands.add_parser(
        "init-docker-env", help="Write unique local Docker secrets to an ignored file; never overwrites"
    )
    env.add_argument("--output", default=".env.docker")
    args = parser.parse_args()
    if args.command == "init-docker-env":
        target = Path(args.output)
        values = {
            "TRUSTSQL_ADMIN_PASSWORD": secrets.token_hex(24),
            "TRUSTSQL_READER_PASSWORD": secrets.token_hex(24),
            "TRUSTSQL_CONTROL_PASSWORD": secrets.token_hex(24),
            "TRUSTSQL_API_TOKEN": secrets.token_hex(32),
            "TRUSTSQL_MODE": "demo",
            "TRUSTSQL_ENVIRONMENT": "development",
            "TRUSTSQL_ALLOWED_HOSTS": "localhost,127.0.0.1",
            "TRUSTSQL_LLM_API_KEY": "",
            "TRUSTSQL_LLM_MODEL": "gpt-4.1-mini",
            "TRUSTSQL_LLM_BASE_URL": "https://api.openai.com/v1",
            "TRUSTSQL_DATAHUB_GRAPHQL_URL": "http://host.docker.internal:8080/api/graphql",
            "TRUSTSQL_DATAHUB_TOKEN": "",
        }
        with target.open("x", encoding="utf-8") as handle:
            handle.write(
                "# Generated local secrets. Do not commit or share.\n"
                + "\n".join(f"{k}={v}" for k, v in values.items())
                + "\n"
            )
        print(f"Created {target}. Secrets were not printed. Read the file locally to connect.")
        return
    settings = Settings()
    if args.command in {"seed", "bootstrap"}:
        if args.command == "seed" and (
            settings.environment == "production" or not settings.warehouse_url.startswith("sqlite:")
        ):
            parser.error(
                "seed is local SQLite only; use bootstrap with an explicit offline PostgreSQL owner URL"
            )
        url = (
            os.environ.get("TRUSTSQL_BOOTSTRAP_URL")
            if args.command == "bootstrap"
            else settings.warehouse_url
        )
        if not url:
            parser.error("bootstrap requires TRUSTSQL_BOOTSTRAP_URL")
        warehouse = make_engine(url)
        control = make_engine(settings.control_database_url)
        try:
            created = seed_warehouse(warehouse)
            ControlStore(control).initialize()
        finally:
            warehouse.dispose()
            control.dispose()
        print(json.dumps({"warehouse": "seeded" if created else "already_seeded", "control_schema": 1}))
    elif args.command == "evaluate":
        from trustsql.evaluation import run_evaluation

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        summary = run_evaluation(settings, output, variant=args.variant, suite=args.suite)
        print(
            json.dumps(
                {
                    "report": str(output),
                    "passed": summary["passed"],
                    "cases": summary["cases"],
                    "label": summary["label"],
                }
            )
        )
        if summary["passed"] != summary["cases"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
