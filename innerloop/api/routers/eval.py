from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..models import EvalStartRequest, OptimizeResponse, ErrorResponse

router = APIRouter()


@router.post("/eval/start", response_model=OptimizeResponse, summary="Start evaluation job")
async def eval_start(request: Request, body: EvalStartRequest):
    reg = request.app.state.registry
    payload = {"__eval__": True, **body.model_dump(exclude_none=True)}
    job, created = await reg.create_job(iterations=1, payload=payload)
    request.state.job_id = job.id
    return OptimizeResponse(job_id=job.id)


@router.get(
    "/eval/{job_id}/events",
    response_class=StreamingResponse,
    response_model=None,
    summary="Stream eval events",
    description="Server-Sent Events stream for evaluation jobs.",
    responses={
        200: {"content": {"text/event-stream": {}}},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def eval_events(request: Request, job_id: UUID) -> StreamingResponse:
    job_id_str = str(job_id)
    request.scope["path"] = f"/v1/optimize/{job_id_str}/events"
    from .optimize import optimize_events

    return await optimize_events(request, job_id_str)
