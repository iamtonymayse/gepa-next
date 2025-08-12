from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ..jobs.registry import JobRegistry

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


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(request: Request, job_id: str) -> Response:
    registry: JobRegistry = request.app.state.registry
    store = request.app.state.store
    if job_id in registry.jobs:
        registry.jobs.pop(job_id, None)
    await store.delete_job(job_id)
    return Response(status_code=204)
