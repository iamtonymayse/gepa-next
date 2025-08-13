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
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
            client_ip = client_ip.split(",")[0].strip()
            query = request.url.query
            if len(query) > 256:
                query = query[:256] + "…"
            headers = {k: v for k, v in request.headers.items()}
            for key in list(headers.keys()):
                if key.lower() == "authorization":
                    headers[key] = "REDACTED"
            allowed = {"x-request-id", "user-agent", "accept", "accept-encoding"}
            headers = {k: v for k, v in headers.items() if k.lower() in allowed}
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
