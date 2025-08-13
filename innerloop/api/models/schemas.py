from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class DatasetSpec(BaseModel):
    name: str
    split: str | None = None

    model_config = {"extra": "forbid"}


class BudgetSpec(BaseModel):
    max_generations: int | None = None
    max_rollouts: int | None = None
    max_cost: float | None = None

    model_config = {"extra": "forbid"}


class OptimizeRequest(BaseModel):
    prompt: str
    context: Dict[str, Any] | None = None
    mode: Literal["default", "gepa"] = "default"
    dataset: DatasetSpec | None = None
    metrics: List[str] | None = None
    budget: BudgetSpec | None = None
    objectives: List[str] | None = None

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Write a haiku",
                    "context": {"topic": "clouds"},
                    "mode": "default",
                }
            ]
        },
    }


class OptimizeResponse(BaseModel):
    job_id: str

    model_config = {
        "json_schema_extra": {"examples": [{"job_id": "123e4567"}]}
    }


class JobState(BaseModel):
    job_id: str
    status: str
    created_at: float
    updated_at: float
    result: Dict[str, Any] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "job_id": "123e4567",
                    "status": "finished",
                    "created_at": 0.0,
                    "updated_at": 1.0,
                    "result": {"proposal": "..."},
                }
            ]
        }
    }


class SSEEnvelope(BaseModel):
    type: Literal[
        "started",
        "progress",
        "finished",
        "failed",
        "cancelled",
        "shutdown",
    ]
    schema_version: int = 1
    job_id: str
    ts: float
    id: int | None = Field(default=None)
    data: Dict[str, Any]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "started",
                    "schema_version": 1,
                    "job_id": "123e4567",
                    "ts": 0.0,
                    "id": 1,
                    "data": {},
                }
            ]
        }
    }
