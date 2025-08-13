from __future__ import annotations

import logging
import sys
import time
import uuid
import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...settings import get_settings

settings = get_settings()
logger = logging.getLogger("gepa")
level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logger.setLevel(level)
if settings.DEBUG_LOG_CONSOLE and not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    logger.addHandler(handler)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Attach/propagate request IDs and log request lifecycle."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.logger = logger
        # redact any header key matching these patterns (case-insensitive)
        self._redact_key_re = re.compile(
            r"(authorization|api[-_]?key|token)", re.IGNORECASE
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            client_ip = request.headers.get(
                "x-forwarded-for", request.client.host if request.client else ""
            )
            client_ip = client_ip.split(",")[0].strip()
            query = request.url.query
            if len(query) > 256:
                query = query[:256] + "…"
            headers = {}
            for k, v in request.headers.items():
                headers[k] = "REDACTED" if self._redact_key_re.search(k) else v
            extra = {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code if response else 500,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id,
                "client_ip": client_ip,
                "headers": headers,
            }
            job_id = getattr(request.state, "job_id", None)
            if job_id:
                extra["job_id"] = job_id
            if query:
                extra["query"] = query
            self.logger.info("request", extra=extra)
            if response:
                response.headers["X-Request-ID"] = request_id
