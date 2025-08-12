from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...settings import get_settings
from ..models import ErrorResponse
from ..metrics import inc


class SizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding MAX_REQUEST_BYTES."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        settings = get_settings()
        if request.method not in {"POST", "PUT", "PATCH"}:
            return await call_next(request)
        limit = settings.MAX_REQUEST_BYTES
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > limit:
                    err = ErrorResponse(
                        code="payload_too_large",
                        message="Payload too large",
                        request_id=request.state.request_id,
                    )
                    inc("oversize_rejected")
                    return JSONResponse(err.model_dump(), status_code=413)
            except ValueError:
                err = ErrorResponse(
                    code="payload_too_large",
                    message="Payload too large",
                    request_id=request.state.request_id,
                )
                inc("oversize_rejected")
                return JSONResponse(err.model_dump(), status_code=413)
            return await call_next(request)
        # No content-length; read stream up to limit
        body = b""
        async for chunk in request.stream():
            body += chunk
            if len(body) > limit:
                err = ErrorResponse(
                    code="payload_too_large",
                    message="Payload too large",
                    request_id=request.state.request_id,
                )
                inc("oversize_rejected")
                return JSONResponse(err.model_dump(), status_code=413)
        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}
        request = Request(request.scope, receive)
        return await call_next(request)
