from datetime import date
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRUSTSQL_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    mode: Literal["demo", "live"] = "demo"
    warehouse_url: str = "sqlite:///var/warehouse.db"
    control_database_url: str = "sqlite:///var/control.db"
    api_token: SecretStr = SecretStr("")
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    max_rows: int = Field(200, ge=1, le=1000)
    query_timeout_seconds: int = Field(5, ge=1, le=30)
    rate_limit_per_minute: int = Field(20, ge=1, le=1000)
    max_concurrent_queries: int = Field(4, ge=1, le=16)
    as_of_date: date = date(2026, 11, 15)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"
    llm_api_key: SecretStr = SecretStr("")
    llm_timeout_seconds: int = Field(30, ge=1, le=90)
    datahub_graphql_url: str = "http://localhost:8080/api/graphql"
    datahub_token: SecretStr = SecretStr("")
    metadata_cache_seconds: int = Field(60, ge=0, le=300)

    @model_validator(mode="after")
    def valid_boundaries(self):
        if self.warehouse_url == self.control_database_url:
            raise ValueError("Warehouse and control connections must be separate.")
        if self.mode == "live" and not self.llm_api_key.get_secret_value():
            raise ValueError("Live mode requires TRUSTSQL_LLM_API_KEY.")
        if self.environment == "production":
            if self.mode != "live":
                raise ValueError("Production requires live mode.")
            if len(self.api_token.get_secret_value()) < 32:
                raise ValueError("Production requires an API token of at least 32 characters.")
            if not all(
                u.startswith("postgresql+psycopg://") for u in [self.warehouse_url, self.control_database_url]
            ):
                raise ValueError("Production requires separate PostgreSQL psycopg connections.")
            if "*" in self.allowed_hosts or not self.allowed_hosts.strip():
                raise ValueError("Production requires explicit allowed hosts.")
            for endpoint in [self.llm_base_url, self.datahub_graphql_url]:
                if urlparse(endpoint).scheme != "https":
                    raise ValueError("Production upstream connections require HTTPS.")
            if not self.datahub_token.get_secret_value():
                raise ValueError("Production requires a DataHub access token.")
        return self
