from __future__ import annotations

from typing import Callable
import hmac
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...settings import get_settings
from ..models import ErrorCode, error_response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        settings = get_settings()
        path = request.url.path

        request_id = getattr(
            request.state, "request_id", request.headers.get("x-request-id") or str(uuid.uuid4())
        )
        request.state.request_id = request_id

        # Public endpoints
        if path.startswith(("/healthz", "/readyz", "/v1/healthz", "/v1/readyz")):
            return await call_next(request)

        # Bypass when OPENROUTER_API_KEY set and no Authorization header
        if (
            path.startswith(("/optimize", "/v1/optimize"))
            and settings.OPENROUTER_API_KEY
            and "authorization" not in request.headers
        ):
            return await call_next(request)

        if not settings.REQUIRE_AUTH:
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return error_response(
                ErrorCode.unauthorized, "Unauthorized", 401, request_id=request_id
            )
        token = auth_header.split(" ", 1)[1]
        valid = any(hmac.compare_digest(token, t) for t in settings.API_BEARER_TOKENS)
        if not valid:
            return error_response(
                ErrorCode.unauthorized, "Unauthorized", 401, request_id=request_id
            )

        return await call_next(request)
