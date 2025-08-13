from __future__ import annotations

from enum import Enum
from typing import Any, Dict

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    unauthorized = "unauthorized"
    not_found = "not_found"
    rate_limited = "rate_limited"
    payload_too_large = "payload_too_large"
    not_cancelable = "not_cancelable"
    sse_backpressure = "sse_backpressure"
    validation_error = "validation_error"
    internal_error = "internal_error"


class APIError(BaseModel):
    code: ErrorCode
    message: str
    details: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: APIError


def error_response(
    code: ErrorCode,
    message: str,
    status_code: int,
    *,
    details: Dict[str, Any] | None = None,
    request_id: str | None = None,
    headers: Dict[str, str] | None = None,
) -> JSONResponse:
    err = APIError(code=code, message=message, details=details or {})
    hdrs = headers.copy() if headers else {}
    if request_id:
        hdrs.setdefault("X-Request-ID", request_id)
    return JSONResponse({"error": err.model_dump()}, status_code=status_code, headers=hdrs)
