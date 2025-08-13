from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

from ..jobs.registry import JobRegistry, JobStatus
from ..models import (
    APIError,
    ErrorCode,
    JobState,
    OptimizeRequest,
    OptimizeResponse,
    error_response,
)
from ..sse import format_sse, prelude_retry_ms, SSE_TERMINALS
from ..metrics import inc
from ...settings import get_settings

router = APIRouter()


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Create optimization job",
    description="Create an optimization job. Use optional Idempotency-Key header to dedupe submissions.",
    responses={401: {"model": APIError}, 429: {"model": APIError}, 413: {"model": APIError}},
)
async def create_optimize_job(
    request: Request,
    body: OptimizeRequest,
    iterations: int = 1,
) -> OptimizeResponse:
    registry: JobRegistry = request.app.state.registry
    idem_key = request.headers.get("Idempotency-Key")
    job, created = await registry.create_job(
        iterations, body.model_dump(), idempotency_key=idem_key
    )
    request.state.job_id = job.id
    if created:
        inc("jobs_created")
    return OptimizeResponse(job_id=job.id)


@router.get("/optimize/{job_id}", response_model=JobState)
async def get_job(request: Request, job_id: str) -> JobState | JSONResponse:
    registry: JobRegistry = request.app.state.registry
    store = request.app.state.store
    job = registry.jobs.get(job_id)
    if job is None:
        record = await store.get_job(job_id)
        if record is None:
            return error_response(
                ErrorCode.not_found, "Job not found", 404, request_id=request.state.request_id
            )
        request.state.job_id = job_id
        return JobState(
            job_id=record["id"],
            status=record["status"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            result=record.get("result"),
        )
    request.state.job_id = job_id
    return JobState(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=job.result,
    )


@router.delete("/optimize/{job_id}", response_model=JobState)
async def cancel_job_endpoint(request: Request, job_id: str):
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if job is None:
        return error_response(
            ErrorCode.not_found, "Job not found", 404, request_id=request.state.request_id
        )
    if job.status != JobStatus.RUNNING:
        return error_response(
            ErrorCode.not_cancelable,
            "Job not cancelable",
            409,
            request_id=request.state.request_id,
        )
    request.state.job_id = job_id
    await registry.cancel_job(job_id)
    return JobState(
        job_id=job_id,
        status=job.status.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=job.result,
    )


@router.get(
    "/optimize/{job_id}/events",
    response_class=StreamingResponse,
    summary="Stream job events",
    description="Server-Sent Events stream. Use Last-Event-ID header to resume from a specific event id.",
)
async def optimize_events(request: Request, job_id: str) -> StreamingResponse:
    registry: JobRegistry = request.app.state.registry
    store = request.app.state.store
    job = registry.jobs.get(job_id)
    if job is None:
        record = await store.get_job(job_id)
        if record is None:
            return error_response(
                ErrorCode.not_found, "Job not found", 404, request_id=request.state.request_id
            )
    request.state.job_id = job_id

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        last_id_header = request.headers.get("last-event-id") or request.query_params.get(
            "last_event_id"
        )
        last_id = int(last_id_header) if last_id_header and last_id_header.isdigit() else 0

        inc("sse_clients", 1)
        yield prelude_retry_ms(settings.SSE_RETRY_MS)
        past_events = await store.events_since(job_id, last_id)
        terminal_sent = False
        for env in past_events:
            yield format_sse(env["type"], env).encode()
            last_id = env["id"]
            if env["type"] in SSE_TERMINALS:
                terminal_sent = True
        if terminal_sent or not job:
            return
        try:
            while True:
                try:
                    envelope = await asyncio.wait_for(
                        job.queue.get(), timeout=settings.SSE_PING_INTERVAL_S
                    )
                    if envelope["id"] <= last_id:
                        continue
                    yield format_sse(envelope["type"], envelope).encode()
                    last_id = envelope["id"]
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
