from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ...domain.objectives import get_objectives
from ...domain.reflection_multirole import update_lessons_journal
from ...domain.reflection_runner import run_reflection
from ...domain.gepa_loop import gepa_loop
from ...domain.judge import judge_scores
from ...settings import get_settings
from ..sse import SSE_TERMINALS
from ..metrics import inc
from .store import JobStore


def _select_best(proposals: list[str]) -> str | None:
    from ...domain.optimize_engine import pareto_filter

    best = pareto_filter(proposals, n=1)
    return best[0] if best else None


def _progress_payload(iteration: int, result: dict, proposals: list[str]) -> dict:
    chosen = _select_best(proposals)
    return {
        "iteration": iteration + 1,
        "summary": result.get("summary"),
        "proposal": chosen,
    }


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"




@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.PENDING
    queue: asyncio.Queue[Dict[str, Any]] = field(init=False)
    next_event_id: int = 1
    task: Optional[asyncio.Task] = None
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    updated_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    terminal_emitted: bool = False

    def __post_init__(self) -> None:
        settings = get_settings()
        self.queue = asyncio.Queue(maxsize=settings.SSE_QUEUE_MAXSIZE)


class JobRegistry:
    def __init__(self, store: JobStore) -> None:
        self.store = store
        self.jobs: Dict[str, Job] = {}
        self._shutdown = False

    async def create_job(
        self, iterations: int, payload: Dict[str, Any], idempotency_key: str | None = None
    ) -> tuple[Job, bool]:
        settings = get_settings()
        now = asyncio.get_event_loop().time()
        if idempotency_key:
            existing = await self.store.get_idempotent(
                idempotency_key, now, settings.IDEMPOTENCY_TTL_S
            )
            if existing:
                job = self.jobs.get(existing)
                if job:
                    return job, False
                record = await self.store.get_job(existing)
                if record:
                    stub = Job(id=record["id"])
                    stub.status = JobStatus(record["status"])
                    stub.created_at = record["created_at"]
                    stub.updated_at = record["updated_at"]
                    stub.result = record.get("result")
                    return stub, False
        job_id = str(uuid.uuid4())
        job = Job(id=job_id)
        self.jobs[job_id] = job
        await self.store.save_job(job)
        job.task = asyncio.create_task(self._run_job(job, iterations, payload))
        if idempotency_key:
            await self.store.save_idempotency(idempotency_key, job_id, now)
        return job, True

    async def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or job.status != JobStatus.RUNNING:
            return False
        if job.task:
            job.task.cancel()
            return True

        # Fallback if no task exists
        job.status = JobStatus.CANCELLED
        await self._emit(job, "cancelled", {})
        await self.store.save_job(job)
        return True

    async def _emit(self, job: Job, event: str, data: Dict[str, Any]) -> None:
        settings = get_settings()
        now = asyncio.get_event_loop().time()
        envelope = {
            "type": event,
            "job_id": job.id,
            "ts": now,
            "data": data,
            "id": job.next_event_id,
        }
        job.next_event_id += 1
        try:
            await asyncio.wait_for(
                job.queue.put(envelope), timeout=settings.SSE_BACKPRESSURE_FAIL_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            job.status = JobStatus.FAILED
            job.result = {"error": "sse_backpressure"}
            inc("jobs_failed")
            fail_env = {
                "type": "failed",
                "job_id": job.id,
                "ts": asyncio.get_event_loop().time(),
                "data": job.result,
                "id": job.next_event_id,
            }
            job.next_event_id += 1
            await self.store.save_event(job.id, fail_env["id"], fail_env)
            try:
                job.queue.put_nowait(fail_env)
            except asyncio.QueueFull:
                pass
            job.terminal_emitted = True
            job.updated_at = fail_env["ts"]
            await self.store.save_job(job)
            return
        await self.store.save_event(job.id, envelope["id"], envelope)
        if event in SSE_TERMINALS:
            job.terminal_emitted = True
            if event == "finished":
                inc("jobs_finished")
            elif event == "failed":
                inc("jobs_failed")
            elif event == "cancelled":
                inc("jobs_cancelled")
        job.updated_at = now
        await self.store.save_job(job)

    async def _run_job(self, job: Job, iterations: int, payload: Dict[str, Any]) -> None:
        settings = get_settings()
        try:
            job.status = JobStatus.RUNNING
            await self._emit(job, "started", {})
            if job.status == JobStatus.FAILED:
                return
            mode = payload.get("mode", "default")
            if mode == "gepa":
                result = await gepa_loop(job, self._emit, payload)
                job.result = result
                job.status = JobStatus.FINISHED
                await self._emit(job, "finished", result)
                return
            iterations = min(iterations, settings.MAX_ITERATIONS)
            prompt = payload.get("prompt", "")
            examples = payload.get("examples") or []
            objective_names: List[str] = payload.get("objectives") or ["brevity", "diversity", "coverage"]
            target_model_id = payload.get("target_model_id") or payload.get("model_id")
            temperature = payload.get("temperature")
            max_tokens = payload.get("max_tokens")
            objectives = get_objectives(objective_names, examples)
            lessons: List[str] = []
            proposals: List[str] = []
            loop = asyncio.get_event_loop()
            start = loop.time()
            deadline = start + settings.MAX_WALL_TIME_S

            def scores_for(text: str) -> Dict[str, float]:
                return {
                    name: fn(text) for name, fn in zip(objective_names, objectives)
                }

            for i in range(iterations):
                if loop.time() > deadline:
                    job.status = JobStatus.FAILED
                    job.result = {"error": "deadline_exceeded"}
                    await self._emit(job, "failed", job.result)
                    return
                result = await run_reflection(
                    prompt=prompt,
                    mode="default",
                    iteration=i,
                    examples=examples,
                    target_model_id=target_model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if loop.time() > deadline:
                    job.status = JobStatus.FAILED
                    job.result = {"error": "deadline_exceeded"}
                    await self._emit(job, "failed", job.result)
                    return
                lessons = update_lessons_journal(lessons, result.get("lessons", []))
                proposal_text = result.get("proposal", "")
                proposals.append(proposal_text)
                det_scores = scores_for(proposal_text) if objective_names else {}
                judge = await judge_scores(prompt, proposal_text, examples, objective_names)
                progress_data = _progress_payload(i, result, proposals)
                if objective_names:
                    progress_data["scores"] = {**det_scores, "judge": judge["scores"]}
                if examples:
                    progress_data["example_ids"] = [e["id"] for e in examples]
                await self._emit(job, "progress", progress_data)
                if loop.time() > deadline:
                    job.status = JobStatus.FAILED
                    job.result = {"error": "deadline_exceeded"}
                    await self._emit(job, "failed", job.result)
                    return
                await asyncio.sleep(0.05)
            final_best = _select_best(proposals) or ""
            det = scores_for(final_best) if objective_names else {}
            judge_final = await judge_scores(prompt, final_best, examples, objective_names)
            result_scores = (
                {**det, "judge": judge_final["scores"]}
                if objective_names
                else {"judge": judge_final["scores"]}
            )
            job.result = {
                "proposal": final_best,
                "lessons": lessons,
                "scores": result_scores,
            }
            job.status = JobStatus.FINISHED
            await self._emit(job, "finished", job.result)
        except asyncio.CancelledError:
            if not job.terminal_emitted:
                job.status = JobStatus.CANCELLED
                await self._emit(job, "cancelled", {})
        except Exception as exc:  # pragma: no cover - unexpected
            job.status = JobStatus.FAILED
            await self._emit(job, "failed", {"error": str(exc)})
        finally:
            job.task = None

    async def reaper_loop(self) -> None:
        settings = get_settings()
        while not self._shutdown:
            now = asyncio.get_event_loop().time()
            to_delete: List[str] = []
            for job_id, job in list(self.jobs.items()):
                if job.status == JobStatus.RUNNING:
                    continue
                ttl_map = {
                    JobStatus.FINISHED: settings.JOB_TTL_FINISHED_S,
                    JobStatus.FAILED: settings.JOB_TTL_FAILED_S,
                    JobStatus.CANCELLED: settings.JOB_TTL_CANCELLED_S,
                }
                ttl = ttl_map.get(job.status)
                if ttl is not None and now - job.updated_at > ttl:
                    to_delete.append(job_id)
            for job_id in to_delete:
                self.jobs.pop(job_id, None)
            await asyncio.sleep(settings.JOB_REAPER_INTERVAL_S)
        for job in self.jobs.values():
            await self._emit(job, "shutdown", {})

    def shutdown(self) -> None:
        self._shutdown = True
        for job in self.jobs.values():
            if job.task and not job.task.done():
                job.task.cancel()
