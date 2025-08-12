from __future__ import annotations

from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Central application configuration.

    All time-to-live (TTL) values and iteration limits are configured here
    to avoid magic numbers sprinkled throughout the codebase. Environment
    variables can override these defaults when deploying.
    """

    max_iterations: int = Field(default=50, description="Maximum iterations allowed for optimization tasks")
    job_ttl_finished_s: int = Field(default=3600, description="Seconds to retain finished or cancelled jobs")
    job_ttl_zombie_s: int = Field(default=300, description="Seconds before a running job without activity is considered a zombie")
    job_ttl_idle_s: int = Field(default=600, description="Seconds to retain idle or pending jobs with no activity")
    job_reaper_interval_s: int = Field(default=60, description="Interval in seconds between registry cleanup runs")
    sse_ping_interval_s: int = Field(default=5, description="Interval in seconds between SSE ping events")
    reflection_timeout_s: int = Field(default=300, description="Timeout in seconds for reflection operations")
    api_key: Optional[str] = Field(default=None, description="Bearer API key for protected endpoints")
    openrouter_api_key: Optional[str] = Field(default=None, description="Alternate key used to bypass auth in test mode")

    class Config:
        env_prefix = ""
        env_file = ".env"
        case_sensitive = False


# A module-level singleton for convenient access
settings = Settings()
