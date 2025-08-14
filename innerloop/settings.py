from __future__ import annotations

from functools import lru_cache
import json
import json as _json
import os
from typing import List, Literal, Optional

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REQUIRE_AUTH: bool = True
    API_BEARER_TOKENS: List[str] = Field(default_factory=list)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=list)
    SSE_RETRY_MS: int = 1500
    SSE_PING_INTERVAL_S: float = 1.0
    SSE_BACKPRESSURE_FAIL_TIMEOUT_S: float = 2.0
    # Max number of SSE events buffered per job before producers apply backpressure.
    SSE_BUFFER_SIZE: int = 200
    MAX_ITERATIONS: int = 4
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG|INFO|WARNING|ERROR
    DEBUG_LOG_CONSOLE: bool = False  # if true, always log to console/stdout
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
    USE_JUDGE_STUB: bool = True
    MODEL_ID: str = "gpt-4o-mini"
    JUDGE_PROVIDER: Literal["openrouter", "openai", "stub"] = "openrouter"
    JUDGE_MODEL_ID: str = "openai:gpt-5-judge"  # fixed judge, not API-settable
    JUDGE_TIMEOUT_S: float = 15.0
    JUDGE_CACHE_SIZE: int = 2048
    JUDGE_QPS_MAX: float = 5.0
    ENABLE_PARETO_V2: bool = True
    PARETO_TOPN: int = 1
    EVALUATION_RUBRIC_DEFAULT: str = "overall quality and clarity"
    TOURNAMENT_SIZE: int = 4
    RECOMBINATION_RATE: float = 0.5
    EARLY_STOP_PATIENCE: int = 3
    RETRIEVAL_MAX_EXAMPLES: int = 4
    RETRIEVAL_MIN_LEN: int = 8
    # Single source of truth for default target model (overrideable per API call)
    TARGET_MODEL_DEFAULT: str = "openai:gpt-4o-mini"
    MAX_CANDIDATES: int = 8
    MAX_EXAMPLES_PER_JOB: int = 16
    MAX_MUTATIONS_PER_ROUND: int = 4
    DETERMINISTIC_SEED: int = 13
    # Determinism & performance budgets
    GEPA_DETERMINISTIC: bool = False
    PERF_BUDGET_P95_JOB_MS: int = 800
    PERF_BUDGET_P95_EVENT_MS: int = 120
    MAX_WALL_TIME_S: float = 15.0
    JOB_STORE: Literal["memory", "sqlite"] = "memory"
    SQLITE_PATH: str = "gepa.db"
    COST_TRACKING_ENABLED: bool = True
    MODEL_PRICES_JSON: str = (
        '{"openai:gpt-5-judge":{"input":0.0,"output":0.0},"openai:gpt-4o-mini":{"input":0.0,"output":0.0}}'
    )
    EVAL_MAX_EXAMPLES: int = 100
    EVAL_MAX_CONCURRENCY: int = 8

    @computed_field
    def MODEL_PRICES(self) -> dict[str, dict[str, float]]:  # noqa: N802
        try:
            return _json.loads(self.MODEL_PRICES_JSON)
        except Exception:
            return {}

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
    settings.TOURNAMENT_SIZE = max(2, int(settings.TOURNAMENT_SIZE))
    settings.RECOMBINATION_RATE = min(1.0, max(0.0, settings.RECOMBINATION_RATE))
    settings.EARLY_STOP_PATIENCE = max(1, int(settings.EARLY_STOP_PATIENCE))
    settings.RETRIEVAL_MAX_EXAMPLES = max(0, int(settings.RETRIEVAL_MAX_EXAMPLES))
    settings.RETRIEVAL_MIN_LEN = max(0, int(settings.RETRIEVAL_MIN_LEN))
    settings.EVAL_MAX_EXAMPLES = max(1, int(settings.EVAL_MAX_EXAMPLES))
    settings.EVAL_MAX_CONCURRENCY = max(1, int(settings.EVAL_MAX_CONCURRENCY))
    return settings


@lru_cache
def _get_settings() -> Settings:
    return Settings()
