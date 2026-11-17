"""Durable redacted audit and atomic rate limits for the low-cost AWS demo."""

import time
from datetime import UTC, datetime

from trustsql.control import digest
from trustsql.errors import TrustSQLError


class DynamoControlStore:
    def __init__(self, table):
        self.table = table

    def ready(self):
        try:
            return self.table.table_status == "ACTIVE"
        except Exception:
            return False

    def consume(self, key, limit, now=None):
        window = int((time.time() if now is None else now) // 60)
        try:
            self.table.update_item(
                Key={"pk": f"RATE#{digest(key)}#{window}", "sk": "RATE"},
                UpdateExpression="SET #n = if_not_exists(#n, :zero) + :one, expires_at = :ttl",
                ConditionExpression="attribute_not_exists(#n) OR #n < :limit",
                ExpressionAttributeNames={"#n": "count"},
                ExpressionAttributeValues={":zero": 0, ":one": 1, ":limit": limit, ":ttl": (window + 3) * 60},
            )
        except Exception as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                raise TrustSQLError(
                    "rate_limited", "The query limit has been reached. Try again in one minute.", 429
                ) from None
            raise TrustSQLError(
                "audit_unavailable", "The audit store is unavailable. Queries are paused.", 503
            ) from None

    def record(
        self,
        *,
        request_id,
        question,
        sql,
        mode,
        status,
        duration_ms,
        tables,
        metadata_source,
        error_code=None,
    ):
        now = datetime.now(UTC).isoformat()
        item = {
            "pk": "RUN",
            "sk": f"{now}#{request_id}",
            "request_id": request_id,
            "created_at": now,
            "question_hash": digest(question),
            "sql_hash": digest(sql) if sql else None,
            "mode": mode,
            "status": status,
            "duration_ms": duration_ms,
            "tables": tables,
            "metadata_source": metadata_source,
            "error_code": error_code,
            "expires_at": int(time.time()) + 7 * 86400,
        }
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
        except Exception:
            raise TrustSQLError(
                "audit_unavailable", "The run could not be recorded. Results are withheld.", 503
            ) from None

    def recent(self):
        try:
            result = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": "RUN"},
                ScanIndexForward=False,
                Limit=30,
            )
            allowed = {
                "request_id",
                "created_at",
                "mode",
                "status",
                "duration_ms",
                "tables",
                "metadata_source",
                "error_code",
            }
            return [
                {k: int(v) if k == "duration_ms" else v for k, v in item.items() if k in allowed}
                for item in result.get("Items", [])
            ]
        except Exception:
            raise TrustSQLError("audit_unavailable", "Run history is temporarily unavailable.", 503) from None
