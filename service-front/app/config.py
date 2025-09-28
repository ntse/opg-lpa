"""Application configuration using Pydantic settings."""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_PATH = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration derived from environment variables."""

    static_path: Path = Field(default_factory=lambda: BASE_PATH / "public" / "assets")
    static_url: str = "/static"
    content_path: Path = Field(default_factory=lambda: BASE_PATH / "content")
    template_path: Path = Field(default_factory=lambda: BASE_PATH / "app" / "templates")
    cors_allow_origins: List[str] = Field(default_factory=list)
    api_base_url: AnyUrl = Field(default="http://localhost:8100")
    api_request_timeout: float = Field(default=10.0, ge=0.1, le=60.0)
    session_secret_key: str = Field(default="development-secret-key")

    model_config = SettingsConfigDict(env_prefix="OPG_LPA_", env_file=".env", extra="ignore")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("static_path", "content_path", "template_path", mode="after")
    @classmethod
    def _ensure_exists(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Path does not exist: {value}")
        return value

    @field_validator("session_secret_key")
    @classmethod
    def _validate_secret(cls, value: str) -> str:
        if len(value) < 16:
            raise ValueError("Session secret key must be at least 16 characters long")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()


__all__ = ["Settings", "get_settings"]
