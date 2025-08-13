from __future__ import annotations

import time
import uuid
from typing import Callable, Dict, Tuple

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...settings import get_settings
from ..models import ErrorResponse
from ..metrics import inc


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket per bearer token for POST /optimize."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        path = request.url.path
        if not (request.method == "POST" and path in {"/optimize", "/v1/optimize"}):
            return await call_next(request)

        settings = get_settings()
        rate = settings.RATE_LIMIT_PER_MIN / 60.0
        burst = settings.RATE_LIMIT_BURST

        request_id = getattr(
            request.state, "request_id", request.headers.get("x-request-id") or str(uuid.uuid4())
        )
        request.state.request_id = request_id

        auth = request.headers.get("authorization", "")
        token = None
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
        elif settings.OPENROUTER_API_KEY and "authorization" not in request.headers:
            token = "anonymous-openrouter"  # nosec B105
        else:
            token = request.client.host or ""  # fallback

        now = time.monotonic()
        tokens, last = self._buckets.get(token, (burst, now))
        tokens = min(burst, tokens + (now - last) * rate)
        if tokens < 1:
            needed = 1 - tokens
            retry_after = max(1, int(needed / rate))
            self._buckets[token] = (tokens, now)
            err = ErrorResponse(
                code="rate_limited",
                message="Rate limit exceeded",
                request_id=request_id,
            )
            inc("rate_limited")
            return JSONResponse(
                err.model_dump(),
                status_code=429,
                headers={"Retry-After": str(retry_after), "X-Request-ID": request_id},
            )
        tokens -= 1
        self._buckets[token] = (tokens, now)
        return await call_next(request)
