import json
import re
import threading
import time
from importlib.resources import files

import httpx

from trustsql.config import Settings
from trustsql.errors import TrustSQLError
from trustsql.http import post_json
from trustsql.models import Dataset


def snapshot() -> list[Dataset]:
    return [
        Dataset.model_validate(d)
        for d in json.loads(files("trustsql").joinpath("fixtures/catalog.json").read_text(encoding="utf-8"))
    ]


class Catalog:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client or httpx.Client(timeout=10, follow_redirects=False)
        self._cached: list[Dataset] | None = None
        self._expires = 0.0
        self._lock = threading.Lock()

    def close(self):
        self.client.close()

    def load(self) -> list[Dataset]:
        if self.settings.mode == "demo":
            return snapshot()
        with self._lock:
            if self._cached is not None and time.monotonic() < self._expires:
                return [d.model_copy(deep=True) for d in self._cached]
            templates = snapshot()
            fragments = "urn name properties { description customProperties { key value } } editableProperties { description } schemaMetadata { fields { fieldPath nativeDataType description } }"
            variables = {f"u{i}": d.urn for i, d in enumerate(templates)}
            declarations = ", ".join(f"$u{i}: String!" for i in range(len(templates)))
            selections = "\n".join(
                f"d{i}: dataset(urn: $u{i}) {{ {fragments} }}" for i in range(len(templates))
            )
            try:
                payload = post_json(
                    self.client,
                    self.settings.datahub_graphql_url,
                    headers={"Authorization": f"Bearer {self.settings.datahub_token.get_secret_value()}"},
                    payload={
                        "query": f"query TrustSQLCatalog({declarations}) {{ {selections} }}",
                        "variables": variables,
                    },
                    max_bytes=2_000_000,
                )
                if payload.get("errors"):
                    raise ValueError("GraphQL error")
                datasets = []
                for i, template in enumerate(templates):
                    entity = payload["data"][f"d{i}"]
                    if not entity or entity["urn"] != template.urn:
                        raise ValueError("missing dataset")
                    properties = entity.get("properties") or {}
                    custom = {p["key"]: p["value"] for p in properties.get("customProperties") or []}
                    fields = (entity.get("schemaMetadata") or {}).get("fields") or []
                    expected_columns = {c.name for c in template.columns}
                    if {f["fieldPath"] for f in fields} != expected_columns:
                        raise ValueError("schema mismatch")
                    description = (entity.get("editableProperties") or {}).get(
                        "description"
                    ) or properties.get("description")
                    if not description:
                        raise ValueError("missing description")
                    datasets.append(
                        Dataset(
                            table=template.table,
                            urn=entity["urn"],
                            description=description[:8000],
                            columns=[
                                {
                                    "name": f["fieldPath"],
                                    "type": f.get("nativeDataType") or "unknown",
                                    "description": (f.get("description") or "")[:2000],
                                }
                                for f in fields
                            ],
                            owner=custom.get("trustsql.owner", "unknown"),
                            certified=custom.get("trustsql.certified") == "true",
                            freshness=custom.get("trustsql.freshness", "unknown"),
                            source="datahub",
                        )
                    )
            except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
                raise TrustSQLError(
                    "metadata_unavailable",
                    "DataHub metadata is unavailable or does not match the approved catalog. Check ingestion and connection settings.",
                    503,
                ) from exc
            self._cached = datasets
            self._expires = time.monotonic() + self.settings.metadata_cache_seconds
            return [d.model_copy(deep=True) for d in datasets]

    def retrieve(self, question: str) -> list[Dataset]:
        datasets = self.load()
        tokens = set(re.findall(r"[a-z]+", question.lower())) - {
            "what",
            "which",
            "the",
            "was",
            "last",
            "month",
            "show",
            "me",
            "our",
        }
        if tokens & {"revenue", "sales", "net", "gross", "refunds", "refunded"}:
            tokens |= {"orders", "order_items", "refunds"}
        dimensions = set()
        if tokens & {"customer", "customers", "segment", "segments", "region", "regions"}:
            dimensions.add("customers")
        if tokens & {"product", "products", "category", "categories"}:
            dimensions.add("products")
        if tokens & {"payment", "payments", "captured"}:
            dimensions.add("payments")

        def score(dataset):
            words = set(re.findall(r"[a-z_]+", dataset.table + " " + dataset.description.lower()))
            return (
                len(tokens & words)
                + (2 if dataset.table in tokens else 0)
                + (6 if dataset.table in dimensions else 0)
            )

        return sorted(datasets, key=score, reverse=True)[:4]
