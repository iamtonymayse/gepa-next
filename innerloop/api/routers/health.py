from __future__ import annotations

from fastapi import APIRouter, Request

from ..metrics import snapshot

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
