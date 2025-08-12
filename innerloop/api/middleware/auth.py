from __future__ import annotations

from typing import Callable
import hmac

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...settings import get_settings
from ..models import ErrorResponse


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        settings = get_settings()
        path = request.url.path

        # Public endpoints
        if path.startswith("/healthz") or path.startswith("/readyz"):
            return await call_next(request)

        # Bypass when OPENROUTER_API_KEY set and no Authorization header
        if path.startswith("/optimize") and settings.OPENROUTER_API_KEY and "authorization" not in request.headers:
            return await call_next(request)

        if not settings.REQUIRE_AUTH:
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            err = ErrorResponse(code="unauthorized", message="Unauthorized", request_id=request.state.request_id)
            return JSONResponse(err.model_dump(), status_code=401)
        token = auth_header.split(" ", 1)[1]
        valid = any(hmac.compare_digest(token, t) for t in settings.API_BEARER_TOKENS)
        if not valid:
            err = ErrorResponse(code="unauthorized", message="Unauthorized", request_id=request.state.request_id)
            return JSONResponse(err.model_dump(), status_code=401)

        return await call_next(request)
