import pytest

from trustsql.dynamo_control import DynamoControlStore
from trustsql.errors import TrustSQLError


class Table:
    table_status = "ACTIVE"

    def update_item(self, **kwargs):
        self.rate = kwargs

    def put_item(self, **kwargs):
        self.item = kwargs["Item"]

    def query(self, **kwargs):
        return {"Items": [self.item]}


def test_dynamo_audit_redacts_and_expires():
    table = Table()
    store = DynamoControlStore(table)
    store.record(
        request_id="id",
        question="private question",
        sql="private SQL",
        mode="demo",
        status="answer",
        duration_ms=5,
        tables=["orders"],
        metadata_source="snapshot",
    )
    assert "private" not in str(table.item)
    assert len(table.item["question_hash"]) == 64
    assert table.item["expires_at"] > 0
    assert store.recent()[0]["duration_ms"] == 5
    assert "question_hash" not in store.recent()[0]
    store.consume("private token", 20, now=120)
    assert "private" not in str(table.rate)
    assert ":limit" in table.rate["ConditionExpression"]
    assert store.ready()


def test_dynamo_storage_failure_fails_closed():
    class Broken(Table):
        def put_item(self, **kwargs):
            raise RuntimeError("sensitive upstream detail")

    with pytest.raises(TrustSQLError) as raised:
        DynamoControlStore(Broken()).record(
            request_id="id",
            question="q",
            sql=None,
            mode="demo",
            status="answer",
            duration_ms=0,
            tables=[],
            metadata_source="snapshot",
        )
    assert raised.value.code == "audit_unavailable"
    assert "sensitive" not in str(raised.value)


def test_dynamo_limit_maps_conditional_failure():
    class Conditional(Exception):
        response = {"Error": {"Code": "ConditionalCheckFailedException"}}

    class Limited(Table):
        def update_item(self, **kwargs):
            raise Conditional()

    with pytest.raises(TrustSQLError) as raised:
        DynamoControlStore(Limited()).consume("k", 1)
    assert raised.value.status == 429
