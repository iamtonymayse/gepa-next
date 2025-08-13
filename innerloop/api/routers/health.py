from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse

from ...settings import Settings, get_settings
from ..metrics import snapshot_metrics_json, snapshot_metrics_text

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/metricsz", response_class=JSONResponse, tags=["ops"])
async def metricsz(settings: Settings = Depends(get_settings)) -> dict:
    return snapshot_metrics_json()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    tags=["ops"],
    responses={
        200: {"content": {"text/plain": {}}},
        401: {"description": "Unauthorized"},
    },
)
async def metrics(settings: Settings = Depends(get_settings)) -> PlainTextResponse:
    """Prometheus-style text exposition format."""
    return PlainTextResponse(snapshot_metrics_text())


@router.get("/version")
async def version(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"version": getattr(settings, "VERSION", "0.1.0")}
