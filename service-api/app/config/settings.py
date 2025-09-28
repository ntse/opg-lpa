from __future__ import annotations

from functools import lru_cache
from pydantic import AliasChoices, BaseModel, Field
from pydantic.alias_generators import to_snake
from pydantic.functional_validators import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    url: str = Field(
        default="postgresql+psycopg_async://lpa:lpa@db:5432/lpa",
        description="SQLAlchemy database URL",
    )
    pool_size: int = 10
    max_overflow: int = 5


class SessionSettings(BaseModel):
    token_ttl_seconds: int = Field(
        default=4500,
        ge=60,
        validation_alias=AliasChoices("SESSION_TOKEN_TTL_SECONDS", "SESSION_TOKEN_TTL", "AUTH_TOKEN_TTL"),
    )


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPG_LPA_",
        extra="ignore",
        env_nested_delimiter="__",
        alias_generator=to_snake,
    )

    stack_name: str = Field(default="local", alias="STACK_NAME")
    stack_environment: str = Field(default="dev", alias="STACK_ENVIRONMENT")

    db_url: str | None = Field(default=None, alias="DB_URL")
    token_ttl_override: int | None = Field(default=None, alias="AUTH_TOKEN_TTL")
    sqs_queue_url: str | None = Field(default=None, alias="COMMON_PDF_QUEUE_URL")
    pdf_queue_warn_threshold: int = Field(default=50, alias="PDF_QUEUE_WARN_THRESHOLD")
    track_my_lpa_endpoint: str | None = Field(default=None, alias="PROCESSING_STATUS_ENDPOINT")
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    session: SessionSettings = Field(default_factory=SessionSettings)

    @model_validator(mode="after")
    def apply_overrides(self) -> "ApiSettings":
        if self.db_url:
            self.db.url = self.db_url
        if self.token_ttl_override:
            self.session.token_ttl_seconds = self.token_ttl_override
        if self.track_my_lpa_endpoint:
            self.track_my_lpa_endpoint = self.track_my_lpa_endpoint.rstrip("/")
            suffix = "/lpa-online-tool/lpas"
            if self.track_my_lpa_endpoint.endswith(suffix):
                self.track_my_lpa_endpoint = self.track_my_lpa_endpoint[: -len(suffix)]
        return self


@lru_cache()
def get_settings() -> ApiSettings:
    return ApiSettings()


__all__ = ["ApiSettings", "DatabaseSettings", "SessionSettings", "get_settings"]
