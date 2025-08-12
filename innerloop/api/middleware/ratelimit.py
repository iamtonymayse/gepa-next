from __future__ import annotations

import time
from typing import Callable, Dict, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...settings import get_settings
from ..models import ErrorResponse
from ..metrics import inc


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket per IP for POST /optimize requests."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        if not (request.method == "POST" and request.url.path == "/optimize"):
            return await call_next(request)
        settings = get_settings()
        rate = settings.RATE_LIMIT_OPTIMIZE_RPS
        burst = settings.RATE_LIMIT_OPTIMIZE_BURST
        ip = request.headers.get("x-forwarded-for", request.client.host or "")
        ip = ip.split(",")[0].strip()
        now = time.monotonic()
        tokens, last = self._buckets.get(ip, (burst, now))
        tokens = min(burst, tokens + (now - last) * rate)
        if tokens < 1:
            needed = 1 - tokens
            retry_after = max(1, int(needed / rate))
            self._buckets[ip] = (tokens, now)
            err = ErrorResponse(
                code="rate_limited",
                message="Rate limit exceeded",
                request_id=request.state.request_id,
            )
            inc("rate_limited")
            return JSONResponse(
                err.model_dump(), status_code=429, headers={"Retry-After": str(retry_after)}
            )
        tokens -= 1
        self._buckets[ip] = (tokens, now)
        return await call_next(request)
