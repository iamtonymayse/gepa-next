from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..jobs.registry import JobRegistry, TERMINAL_EVENTS
from ...settings import get_settings

router = APIRouter()


@router.post("/optimize")
async def create_optimize_job(request: Request, iterations: int = 1) -> dict[str, str]:
    registry: JobRegistry = request.app.state.registry
    job = registry.create_job(iterations, {})
    return {"job_id": job.id}


@router.get("/optimize/{job_id}/events")
async def optimize_events(request: Request, job_id: str) -> StreamingResponse:
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[str, None]:
        yield f"retry: {settings.SSE_RETRY_MS}\n\n"
        while True:
            try:
                event, data = await asyncio.wait_for(
                    job.queue.get(), timeout=settings.SSE_PING_INTERVAL_S
                )
                yield _format_sse_event(event, data)
                if event in TERMINAL_EVENTS:
                    break
            except asyncio.TimeoutError:
                yield ":\n\n"
            if await request.is_disconnected():
                break

    headers = {
        "Cache-Control": "no-store",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


def _format_sse_event(event: str, data: dict) -> str:
    return f"event: {event}\n" + f"data: {json.dumps(data, separators=(',', ':'))}\n\n"
