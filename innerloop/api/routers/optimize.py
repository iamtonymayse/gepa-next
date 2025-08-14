from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ...settings import get_settings
from ..jobs.registry import JobRegistry, JobStatus
from ..metrics import inc
from ..models import ErrorCode, ErrorResponse, JobState, OptimizeRequest, OptimizeResponse, error_response
from ..sse import SSE_TERMINALS, format_sse, prelude_retry_ms

router = APIRouter()


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Create optimization job",
    description="Create an optimization job. Use optional Idempotency-Key header to dedupe submissions.",
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
    },
)
async def create_optimize_job(
    request: Request,
    body: OptimizeRequest,
    iterations: int = 1,
) -> OptimizeResponse:
    if iterations < 1:
        return error_response(
            ErrorCode.validation_error,
            "iterations must be >= 1",
            422,
            request_id=request.state.request_id,
        )
    registry: JobRegistry = request.app.state.registry
    idem_key = request.headers.get("Idempotency-Key")
    job, created = await registry.create_job(iterations, body.model_dump(), idempotency_key=idem_key)
    request.state.job_id = job.id
    if created:
        inc("jobs_created")
    return OptimizeResponse(job_id=job.id)


@router.get(
    "/optimize/{job_id}",
    response_model=JobState,
    responses={404: {"model": ErrorResponse}},
)
async def get_job(request: Request, job_id: str) -> JobState | JSONResponse:
    registry: JobRegistry = request.app.state.registry
    store = request.app.state.store
    job = registry.jobs.get(job_id)
    if job is None:
        record = await store.get_job(job_id)
        if record is None:
            return error_response(ErrorCode.not_found, "Job not found", 404, request_id=request.state.request_id)
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


@router.delete(
    "/optimize/{job_id}",
    response_model=JobState,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def cancel_job_endpoint(request: Request, job_id: str):
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if job is None:
        return error_response(ErrorCode.not_found, "Job not found", 404, request_id=request.state.request_id)
    if job.status != JobStatus.RUNNING:
        return error_response(
            ErrorCode.not_cancelable,
            "Job not cancelable",
            409,
            request_id=request.state.request_id,
        )
    request.state.job_id = job_id
    await registry.cancel_job(job_id)
    # Re-read after mutation to avoid returning a stale reference. If the job
    # task was running, give the event loop a moment to process the cancellation
    # so that the status reflects "cancelled".
    j = registry.jobs.get(job_id) or job
    if j.status == JobStatus.RUNNING:
        await asyncio.sleep(0)
        j = registry.jobs.get(job_id) or j
    return JobState(
        job_id=job_id,
        status=j.status.value,
        created_at=j.created_at,
        updated_at=j.updated_at,
        result=j.result,
    )


@router.get(
    "/optimize/{job_id}/events",
    response_class=StreamingResponse,
    summary="Stream job events",
    description="Server-Sent Events stream. Use Last-Event-ID header to resume from a specific event id.",
    responses={
        200: {"content": {"text/event-stream": {}}},
        401: {"description": "Unauthorized"},
        404: {"description": "Job not found"},
    },
)
async def optimize_events(request: Request, job_id: str) -> StreamingResponse:
    registry: JobRegistry = request.app.state.registry
    store = request.app.state.store
    job = registry.jobs.get(job_id)
    if job is None:
        record = await store.get_job(job_id)
        if record is None:
            return error_response(ErrorCode.not_found, "Job not found", 404, request_id=request.state.request_id)
    request.state.job_id = job_id

    settings = get_settings()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        last_id_header = request.headers.get("last-event-id") or request.query_params.get("last_event_id")
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
                    envelope = await asyncio.wait_for(job.queue.get(), timeout=settings.SSE_PING_INTERVAL_S)
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
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
