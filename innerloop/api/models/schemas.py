from __future__ import annotations

from typing import Any, Dict, List, Literal

from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationInfo


class DatasetSpec(BaseModel):
    name: str
    split: str | None = None

    model_config = {"extra": "forbid"}


class BudgetSpec(BaseModel):
    max_generations: int | None = None
    max_rollouts: int | None = None
    max_cost: float | None = None

    model_config = {"extra": "forbid"}


class ExampleIn(BaseModel):
    id: str | None = None
    name: str | None = None
    input: str
    expected: str | None = None
    tags: List[str] | None = None

    model_config = {"extra": "forbid"}


class Example(ExampleIn):
    id: str


class ObjectiveSpec(str, Enum):
    brevity = "brevity"
    diversity = "diversity"
    coverage = "coverage"


class OptimizeRequest(BaseModel):
    prompt: str
    context: Dict[str, Any] | None = None
    mode: Literal["default", "gepa"] = "default"
    dataset: DatasetSpec | None = None
    metrics: List[str] | None = None
    budget: BudgetSpec | None = None
    examples: List[ExampleIn] | None = None
    objectives: List[str] | None = None
    seed: int | None = None
    target_model_id: str | None = None
    model_id: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None

    @field_validator("examples", mode="before")
    @classmethod
    def _coerce_examples(cls, v):
        if not v:
            return None
        normalized: List[Dict[str, Any]] = []
        for item in v:
            if isinstance(item, BaseModel):
                data = item.model_dump()
            elif isinstance(item, dict):
                data = dict(item)
            else:
                raise TypeError("Invalid example type")
            ex_id = data.get("id")
            data["id"] = str(ex_id) if ex_id is not None else str(uuid4())
            normalized.append(data)
        return normalized

    @field_validator("target_model_id")
    @classmethod
    def _alias_model_id(cls, v, info: ValidationInfo):
        data = info.data
        return v or data.get("model_id")

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Write a haiku",
                    "examples": [{"input": "long text", "expected": "short"}],
                    "objectives": ["brevity", "diversity", "coverage"],
                    "target_model_id": "gpt-4o-mini",
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
                    "type": "progress",
                    "schema_version": 1,
                    "job_id": "123e4567",
                    "ts": 0.0,
                    "id": 1,
                    "data": {"proposal": "text", "scores": {"brevity": -5.0}},
                }
            ]
        }
    }
