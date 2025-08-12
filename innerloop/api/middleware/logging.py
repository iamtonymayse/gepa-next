from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Attach/propagate request IDs and log request lifecycle."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("gepa")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        # Start log
        self.logger.info(
            "start", extra={"method": request.method, "path": request.url.path, "request_id": request_id}
        )
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        # Finish log
        self.logger.info(
            "finish",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "request_id": request_id,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
