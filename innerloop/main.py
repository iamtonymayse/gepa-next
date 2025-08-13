from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .settings import get_settings
from .api.middleware.auth import AuthMiddleware
from .api.middleware.logging import LoggingMiddleware
from .api.middleware.ratelimit import RateLimitMiddleware
from .api.middleware.limits import SizeLimitMiddleware
from .api.middleware.deprecation import DeprecationMiddleware
from .api.routers.health import router as health_router
from .api.routers.optimize import router as optimize_router
from .api.routers.admin import router as admin_router
from .api.routers.examples import router as examples_router
from .api.jobs.registry import JobRegistry
from .api.jobs.store import JobStore, MemoryJobStore, SQLiteJobStore
from .api.models import ErrorCode, error_response
from .domain.engine import close_provider
from .domain.examples_store import ExampleStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store: JobStore
    if settings.JOB_STORE == "sqlite":
        store = await SQLiteJobStore.create(settings.SQLITE_PATH)
    else:
        store = MemoryJobStore()
    registry = JobRegistry(store)
    app.state.registry = registry
    app.state.store = store
    app.state.examples = ExampleStore()
    reaper_task = asyncio.create_task(registry.reaper_loop())
    try:
        yield
    finally:
        registry.shutdown()
        await store.close()
        reaper_task.cancel()
        with suppress(Exception, asyncio.CancelledError):
            await reaper_task
        # Close any cached external provider clients (if used)
        with suppress(Exception):
            await close_provider()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.SERVICE_NAME, lifespan=lifespan)

    if settings.CORS_ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ALLOWED_ORIGINS,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Middleware order matters: Logging→Auth→RateLimit→SizeLimit.
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SizeLimitMiddleware)
    app.add_middleware(DeprecationMiddleware)

    # Versioned routers
    app.include_router(health_router, prefix="/v1", tags=["v1"])
    app.include_router(optimize_router, prefix="/v1", tags=["v1"])
    app.include_router(examples_router, prefix="/v1", tags=["examples"])
    app.include_router(admin_router, prefix="/v1/admin", tags=["admin"])

    # Backward-compatible unversioned aliases (hidden from schema)
    app.include_router(health_router, include_in_schema=False)
    app.include_router(optimize_router, include_in_schema=False)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:  # pragma: no cover - simple
        return error_response(
            ErrorCode.validation_error,
            "Invalid request",
            422,
            request_id=getattr(request.state, "request_id", None),
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - simple
        return error_response(
            ErrorCode.internal_error,
            "Internal server error",
            500,
            request_id=getattr(request.state, "request_id", None),
        )

    return app


app = create_app()
