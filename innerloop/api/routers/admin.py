from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ..jobs.registry import JobRegistry, JobStatus
from ..models import ErrorCode, ErrorResponse, JobState, error_response

router = APIRouter()


@router.get("/jobs")
async def list_jobs(request: Request) -> dict:
    store = request.app.state.store
    jobs = await store.list_jobs()
    return {
        "jobs": [
            {
                "job_id": j["id"],
                "status": j["status"],
                "created_at": j["created_at"],
                "updated_at": j["updated_at"],
            }
            for j in jobs
        ]
    }


@router.get(
    "/jobs/{job_id}",
    response_model=JobState,
    responses={404: {"model": ErrorResponse}},
)
async def get_job(request: Request, job_id: str) -> JobState | Response:
    store = request.app.state.store
    record = await store.get_job(job_id)
    if not record:
        return error_response(
            ErrorCode.not_found, "Job not found", 404, request_id=request.state.request_id
        )
    return JobState(
        job_id=record["id"],
        status=record["status"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
        result=record.get("result"),
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(request: Request, job_id: str) -> Response:
    registry: JobRegistry = request.app.state.registry
    store = request.app.state.store
    if job_id in registry.jobs:
        registry.jobs.pop(job_id, None)
    await store.delete_job(job_id)
    return Response(status_code=204)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobState,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def cancel_job(request: Request, job_id: str) -> JobState | Response:
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if not job:
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
    await registry.cancel_job(job_id)
    return JobState(
        job_id=job_id,
        status=job.status.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result=job.result,
    )
