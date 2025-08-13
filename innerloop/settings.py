from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Literal
import os
import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REQUIRE_AUTH: bool = True
    API_BEARER_TOKENS: List[str] = Field(default_factory=list)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=list)
    SSE_RETRY_MS: int = 1500
    SSE_QUEUE_MAXSIZE: int = 100
    SSE_PING_INTERVAL_S: float = 1.0
    SSE_BACKPRESSURE_FAIL_TIMEOUT_S: float = 2.0
    SSE_BUFFER_SIZE: int = 200
    MAX_ITERATIONS: int = 10
    MAX_REQUEST_BYTES: int = 64_000
    RATE_LIMIT_PER_MIN: int = 60
    RATE_LIMIT_BURST: int = 30
    # legacy names for backward compatibility
    RATE_LIMIT_OPTIMIZE_RPS: float | None = None
    RATE_LIMIT_OPTIMIZE_BURST: int | None = None
    JOB_REAPER_INTERVAL_S: float = 2.0
    JOB_TTL_FINISHED_S: float = 30.0
    JOB_TTL_FAILED_S: float = 120.0
    JOB_TTL_CANCELLED_S: float = 60.0
    SERVICE_NAME: str = "gepa-next"
    SERVICE_ENV: str = "dev"
    IDEMPOTENCY_TTL_S: float = 600.0
    USE_MODEL_STUB: bool = True
    MODEL_ID: str = "gpt-4o-mini"
    TARGET_DEFAULT_MODEL_ID: str = "gpt-4o-mini"
    JUDGE_PROVIDER: Literal["openrouter", "openai"] = "openrouter"
    JUDGE_MODEL_ID: str = "gpt-5"
    JUDGE_TIMEOUT_S: float = 10.0
    MAX_WALL_TIME_S: float = 15.0
    JOB_STORE: Literal["memory", "sqlite"] = "memory"
    SQLITE_PATH: str = "gepa.db"

    @field_validator("API_BEARER_TOKENS", "CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_commas(cls, v: object) -> List[str]:
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                except (json.JSONDecodeError, TypeError, ValueError):
                    parsed = None
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed]
            return [item.strip() for item in s.split(",") if item.strip()]
        if isinstance(v, list):
            return v
        return []


def get_settings() -> Settings:
    settings = _get_settings()
    if "SSE_BACKPRESSURE_FAIL_TIMEOUT_S" not in os.environ:
        settings.SSE_BACKPRESSURE_FAIL_TIMEOUT_S = settings.SSE_PING_INTERVAL_S * 2
    # map legacy rate limit settings if provided
    if settings.RATE_LIMIT_OPTIMIZE_RPS is not None:
        settings.RATE_LIMIT_PER_MIN = int(settings.RATE_LIMIT_OPTIMIZE_RPS * 60)
    if settings.RATE_LIMIT_OPTIMIZE_BURST is not None:
        settings.RATE_LIMIT_BURST = settings.RATE_LIMIT_OPTIMIZE_BURST
    return settings


@lru_cache
def _get_settings() -> Settings:
    return Settings()
