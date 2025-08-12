from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REQUIRE_AUTH: bool = True
    API_BEARER_TOKENS: List[str] = Field(default_factory=list)
    OPENROUTER_API_KEY: Optional[str] = None
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=list)
    SSE_RETRY_MS: int = 1500
    SSE_QUEUE_MAXSIZE: int = 100
    SSE_PING_INTERVAL_S: float = 1.0
    MAX_ITERATIONS: int = 10
    JOB_REAPER_INTERVAL_S: float = 2.0
    JOB_TTL_FINISHED_S: float = 30.0
    JOB_TTL_FAILED_S: float = 120.0
    JOB_TTL_CANCELLED_S: float = 60.0
    SERVICE_NAME: str = "gepa-next"
    SERVICE_ENV: str = "dev"

    @field_validator("API_BEARER_TOKENS", "CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_commas(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return v
        return []


def get_settings() -> Settings:
    return _get_settings()


@lru_cache
def _get_settings() -> Settings:
    return Settings()
