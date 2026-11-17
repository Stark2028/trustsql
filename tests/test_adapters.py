import json

import httpx
import pytest
from pydantic import SecretStr

from trustsql.catalog import Catalog, snapshot
from trustsql.errors import TrustSQLError
from trustsql.planner import LLMPlanner


def live_settings(settings):
    return settings.model_copy(update={"mode": "live", "llm_api_key": SecretStr("test-key")})


def datahub_payload():
    return {
        "data": {
            f"d{i}": {
                "urn": d.urn,
                "name": d.table,
                "properties": {
                    "description": d.description,
                    "customProperties": [{"key": "trustsql.certified", "value": "true"}],
                },
                "schemaMetadata": {
                    "fields": [
                        {"fieldPath": c.name, "nativeDataType": c.type, "description": c.description}
                        for c in d.columns
                    ]
                },
            }
            for i, d in enumerate(snapshot())
        }
    }


def test_datahub_graphql_contract_and_cache(settings):
    requests = []

    def handle(request):
        requests.append(request)
        assert "query TrustSQLCatalog" in json.loads(request.content)["query"]
        return httpx.Response(200, json=datahub_payload())

    catalog = Catalog(live_settings(settings), httpx.Client(transport=httpx.MockTransport(handle)))
    try:
        assert all(d.source == "datahub" for d in catalog.load())
        catalog.load()
        assert len(requests) == 1
    finally:
        catalog.close()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(200, json={"errors": [{"message": "private upstream detail"}]}),
        httpx.Response(200, json={"data": {}}),
        httpx.Response(200, json=[]),
    ],
)
def test_datahub_failure_never_falls_back_to_snapshot(settings, response):
    catalog = Catalog(
        live_settings(settings), httpx.Client(transport=httpx.MockTransport(lambda _: response))
    )
    try:
        with pytest.raises(TrustSQLError) as raised:
            catalog.load()
        assert raised.value.code == "metadata_unavailable"
        assert "private" not in str(raised.value)
    finally:
        catalog.close()


def test_llm_structured_request_contract(settings):
    def handle(request):
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["response_format"]["json_schema"]["strict"] is True
        assert "2026-10-01" in body["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "status": "clarification",
                                    "sql": None,
                                    "explanation": "Gross or net?",
                                    "citations": [],
                                }
                            )
                        }
                    }
                ]
            },
        )

    planner = LLMPlanner(live_settings(settings), httpx.Client(transport=httpx.MockTransport(handle)))
    try:
        assert planner.plan("Revenue?", snapshot()).status == "clarification"
    finally:
        planner.close()


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        '{"status":"answer","sql":null,"explanation":"bad","citations":[]}',
        '{"status":"answer","sql":"SELECT * FROM orders","explanation":"bad","citations":[],"extra":"bad"}',
    ],
)
def test_malformed_model_output_is_not_executed(settings, content):
    planner = LLMPlanner(
        live_settings(settings),
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})
            )
        ),
    )
    try:
        with pytest.raises(TrustSQLError) as raised:
            planner.plan("Question", snapshot())
        assert raised.value.code == "model_unavailable"
    finally:
        planner.close()


def test_upstream_response_stops_at_byte_limit():
    from trustsql.http import post_json

    class LargeStream(httpx.SyncByteStream):
        count = 0

        def __iter__(self):
            for _ in range(100):
                self.count += 1
                yield b"x" * 16384

    stream = LargeStream()
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))) as client:
        with pytest.raises(ValueError, match="limit"):
            post_json(client, "https://example.com", headers={}, payload={}, max_bytes=20000)
    assert stream.count < 5
