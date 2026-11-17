from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Column(BaseModel):
    name: str
    type: str
    description: str = ""


class Dataset(BaseModel):
    table: str
    urn: str
    description: str
    columns: list[Column]
    owner: str = "Analytics Engineering"
    certified: bool = False
    freshness: str = "unknown"
    source: str = "snapshot"


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=4, max_length=2000)

    @model_validator(mode="after")
    def meaningful_question(self):
        self.question = self.question.strip()
        if len(self.question) < 4 or any(ord(c) < 32 and c not in "\n\t" for c in self.question):
            raise ValueError("Enter a question of at least four readable characters.")
        return self


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["answer", "clarification", "refusal"]
    sql: str | None = Field(default=None, max_length=12000)
    explanation: str = Field(max_length=2000)
    citations: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def answer_needs_sql(self):
        if self.status == "answer" and not (self.sql and self.sql.strip()):
            raise ValueError("An answer requires SQL.")
        if self.status != "answer" and self.sql:
            raise ValueError("Clarifications and refusals cannot include executable SQL.")
        return self


class Stage(BaseModel):
    name: str
    status: str
    detail: str


class Answer(BaseModel):
    request_id: str
    status: Literal["answer", "clarification", "refusal"]
    mode: str
    explanation: str
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    evidence: list[Dataset] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stages: list[Stage] = Field(default_factory=list)
    duration_ms: int = 0
    inspection: dict[str, Any] | None = None


class InspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sql: str = Field(min_length=4, max_length=6000)
    changed_table: str | None = Field(default=None, max_length=100)
    changed_column: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def column_needs_table(self):
        if self.changed_column and not self.changed_table:
            raise ValueError("A changed column requires a table")
        return self
