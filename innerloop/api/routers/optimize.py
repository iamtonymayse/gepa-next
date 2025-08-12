from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

from ..jobs.registry import JobRegistry, JobStatus
from ..models import ErrorResponse
from ..sse import format_sse, prelude_retry_ms, SSE_TERMINALS
from ..metrics import inc
from ...settings import get_settings

router = APIRouter()


@router.post("/optimize")
async def create_optimize_job(request: Request, iterations: int = 1) -> dict[str, str]:
    registry: JobRegistry = request.app.state.registry
    job = registry.create_job(iterations, {})
    request.state.job_id = job.id
    inc("jobs_created")
    return {"job_id": job.id}


@router.get("/optimize/{job_id}")
async def get_job(request: Request, job_id: str) -> dict:
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if job is None:
        err = ErrorResponse(code="not_found", message="Job not found", request_id=request.state.request_id)
        return JSONResponse(err.model_dump(), status_code=404)
    request.state.job_id = job_id
    return {
        "job_id": job.id,
        "status": job.status.value,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "result": job.result,
    }


@router.delete("/optimize/{job_id}")
async def cancel_job_endpoint(request: Request, job_id: str) -> dict:
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if job is None:
        err = ErrorResponse(code="not_found", message="Job not found", request_id=request.state.request_id)
        return JSONResponse(err.model_dump(), status_code=404)
    if job.status != JobStatus.RUNNING:
        err = ErrorResponse(code="not_cancelable", message="Job not cancelable", request_id=request.state.request_id)
        return JSONResponse(err.model_dump(), status_code=409)
    request.state.job_id = job_id
    await registry.cancel_job(job_id)
    return {"job_id": job_id, "status": job.status.value}


@router.get("/optimize/{job_id}/events")
async def optimize_events(request: Request, job_id: str) -> StreamingResponse:
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if job is None:
        err = ErrorResponse(code="not_found", message="Job not found", request_id=request.state.request_id)
        return JSONResponse(err.model_dump(), status_code=404)
    request.state.job_id = job_id

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        inc("sse_clients", 1)
        yield prelude_retry_ms(settings.SSE_RETRY_MS)
        try:
            while True:
                try:
                    envelope = await asyncio.wait_for(
                        job.queue.get(), timeout=settings.SSE_PING_INTERVAL_S
                    )
                    yield format_sse(envelope["type"], envelope).encode()
                    if envelope["type"] in SSE_TERMINALS:
                        break
                except asyncio.TimeoutError:
                    yield b":\n\n"
                if await request.is_disconnected():
                    break
        except (GeneratorExit, asyncio.CancelledError):
            return
        finally:
            inc("sse_clients", -1)

    headers = {
        "Cache-Control": "no-store",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
