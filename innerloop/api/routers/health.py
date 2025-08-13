from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from ..metrics import snapshot, prometheus

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/metricsz")
async def metricsz(request: Request) -> dict:
    return snapshot()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics",
    description="Exposes Prometheus metrics in text format.",
    responses={
        200: {
            "content": {
                "text/plain": {
                    "schema": {
                        "type": "string",
                        "description": "Prometheus exposition",
                    }
                }
            },
            "description": "Prometheus metrics",
        }
    },
)
async def metrics_prom(request: Request) -> PlainTextResponse:
    """Prometheus text exposition"""
    text = prometheus()
    return PlainTextResponse(text, media_type="text/plain; version=0.0.4")
