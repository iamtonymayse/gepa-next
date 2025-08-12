from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..jobs.registry import JobRegistry, JobStatus
from ..models import ErrorResponse

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


@router.get("/jobs/{job_id}")
async def get_job(request: Request, job_id: str):
    store = request.app.state.store
    record = await store.get_job(job_id)
    if not record:
        err = ErrorResponse(code="not_found", message="Job not found", request_id=request.state.request_id)
        return JSONResponse(err.model_dump(), status_code=404)
    return {
        "job_id": record["id"],
        "status": record["status"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "result": record.get("result"),
    }


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(request: Request, job_id: str) -> Response:
    registry: JobRegistry = request.app.state.registry
    store = request.app.state.store
    if job_id in registry.jobs:
        registry.jobs.pop(job_id, None)
    await store.delete_job(job_id)
    return Response(status_code=204)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(request: Request, job_id: str):
    registry: JobRegistry = request.app.state.registry
    job = registry.jobs.get(job_id)
    if not job:
        err = ErrorResponse(code="not_found", message="Job not found", request_id=request.state.request_id)
        return JSONResponse(err.model_dump(), status_code=404)
    if job.status != JobStatus.RUNNING:
        err = ErrorResponse(code="not_cancelable", message="Job not cancelable", request_id=request.state.request_id)
        return JSONResponse(err.model_dump(), status_code=409)
    await registry.cancel_job(job_id)
    return {"job_id": job_id, "status": job.status.value}
