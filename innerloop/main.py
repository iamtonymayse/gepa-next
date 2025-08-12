from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import get_settings
from .api.middleware.auth import AuthMiddleware
from .api.middleware.logging import LoggingMiddleware
from .api.middleware.ratelimit import RateLimitMiddleware
from .api.middleware.limits import SizeLimitMiddleware
from .api.routers.health import router as health_router
from .api.routers.optimize import router as optimize_router
from .api.routers.admin import router as admin_router
from .api.jobs.registry import JobRegistry
from .api.jobs.store import JobStore, MemoryJobStore, SQLiteJobStore


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
    reaper_task = asyncio.create_task(registry.reaper_loop())
    try:
        yield
    finally:
        registry.shutdown()
        await store.close()
        reaper_task.cancel()
        with suppress(Exception, asyncio.CancelledError):
            await reaper_task


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

    app.add_middleware(SizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Versioned routers
    app.include_router(health_router, prefix="/v1", tags=["v1"])
    app.include_router(optimize_router, prefix="/v1", tags=["v1"])
    app.include_router(admin_router, prefix="/v1/admin", tags=["admin"])

    # Backward-compatible unversioned aliases (hidden from schema)
    app.include_router(health_router, include_in_schema=False)
    app.include_router(optimize_router, include_in_schema=False)

    return app


app = create_app()
