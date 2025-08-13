from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from ..models import EvalStartRequest, OptimizeResponse, ErrorCode, error_response
from ...settings import get_settings
from ..sse import prelude_retry_ms, format_sse, SSE_TERMINALS
import asyncio

router = APIRouter()


@router.post("/eval/start", response_model=OptimizeResponse, summary="Start evaluation job")
async def eval_start(request: Request, body: EvalStartRequest):
    reg = request.app.state.registry
    payload = {"__eval__": True, **body.model_dump(exclude_none=True)}
    job, created = await reg.create_job(iterations=1, payload=payload)
    request.state.job_id = job.id
    return OptimizeResponse(job_id=job.id)


@router.get("/eval/{job_id}/events", response_class=StreamingResponse)
async def eval_events(request: Request, job_id: str):
    request.scope["path"] = f"/v1/optimize/{job_id}/events"
    from .optimize import optimize_events

    return await optimize_events(request, job_id)
