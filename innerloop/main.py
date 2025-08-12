from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import get_settings
from .api.middleware.auth import AuthMiddleware
from .api.routers.health import router as health_router
from .api.routers.optimize import router as optimize_router
from .api.jobs.registry import JobRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = JobRegistry()
    app.state.registry = registry
    reaper_task = asyncio.create_task(registry.reaper_loop())
    try:
        yield
    finally:
        registry.shutdown()
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

    app.add_middleware(AuthMiddleware)
    app.include_router(health_router)
    app.include_router(optimize_router)

    return app


app = create_app()
