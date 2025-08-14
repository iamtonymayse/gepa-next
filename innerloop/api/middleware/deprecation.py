from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class DeprecationMiddleware(BaseHTTPMiddleware):
    """Adds Deprecation headers to legacy unversioned routes."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._map = {
            "/healthz": "/v1/healthz",
            "/readyz": "/v1/readyz",
            "/optimize": "/v1/optimize",
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        response = await call_next(request)
        path = request.url.path
        for old, new in self._map.items():
            if path == old or path.startswith(old + "/"):
                response.headers["Deprecation"] = "true"
                response.headers["Link"] = f'<{new}>; rel="successor-version"'
                break
        return response
