from __future__ import annotations

from typing import Callable
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...settings import get_settings
from ..metrics import inc
from ..models import ErrorCode, error_response


class SizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding MAX_REQUEST_BYTES."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        settings = get_settings()
        if request.method not in {"POST", "PUT", "PATCH"}:
            return await call_next(request)
        limit = settings.MAX_REQUEST_BYTES
        request_id = getattr(
            request.state,
            "request_id",
            request.headers.get("x-request-id") or str(uuid.uuid4()),
        )
        request.state.request_id = request_id
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > limit:
                    inc("oversize_rejected")
                    return error_response(
                        ErrorCode.payload_too_large,
                        "Payload too large",
                        413,
                        request_id=request_id,
                    )
            except ValueError:
                inc("oversize_rejected")
                return error_response(
                    ErrorCode.payload_too_large,
                    "Payload too large",
                    413,
                    request_id=request_id,
                )
            return await call_next(request)
        # No content-length; read stream up to limit
        body = b""
        async for chunk in request.stream():
            body += chunk
            if len(body) > limit:
                inc("oversize_rejected")
                return error_response(
                    ErrorCode.payload_too_large,
                    "Payload too large",
                    413,
                    request_id=request_id,
                )

        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, receive)
        return await call_next(request)
