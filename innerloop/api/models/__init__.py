"""API models for GEPA."""

from .errors import APIError, ErrorCode, ErrorResponse, error_response
from .schemas import (
    EvalStartRequest,
    Example,
    ExampleIn,
    JobState,
    ObjectiveSpec,
    OptimizeRequest,
    OptimizeResponse,
    SSEEnvelope,
)

__all__ = [
    "OptimizeRequest",
    "OptimizeResponse",
    "JobState",
    "SSEEnvelope",
    "ExampleIn",
    "Example",
    "EvalStartRequest",
    "ObjectiveSpec",
    "APIError",
    "ErrorCode",
    "ErrorResponse",
    "error_response",
]
