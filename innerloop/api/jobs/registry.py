from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ...domain.objectives import get_objectives
from ...domain.gepa_loop import gepa_loop
from ...domain.judge import judge_scores
from ...domain.mutations import mutate_prompt
from ...domain.recombination import recombine
from ...domain.optimize_engine import pareto_filter, tournament_rank
from ...domain.retrieval import retrieve
from ...settings import get_settings
from ..sse import SSE_TERMINALS
from ..metrics import inc
from .store import JobStore


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
            recombination_rate = (
                payload.get("recombination_rate") or settings.RECOMBINATION_RATE
            )
            tournament_size = (
                payload.get("tournament_size") or settings.TOURNAMENT_SIZE
            )
            early_stop_patience = (
                payload.get("early_stop_patience") or settings.EARLY_STOP_PATIENCE
            )
            task = prompt or (examples[0]["input"] if examples else "")
            retrieved = await retrieve(task, settings.RETRIEVAL_MAX_EXAMPLES, self.store)
            examples = (examples + retrieved)[: settings.MAX_EXAMPLES_PER_JOB]
            objectives = get_objectives(objective_names, examples)
            loop = asyncio.get_event_loop()
            start = loop.time()
            deadline = start + settings.MAX_WALL_TIME_S
            seed = payload.get("seed") or settings.DETERMINISTIC_SEED

            def scores_for(text: str) -> Dict[str, float]:
                return {name: fn(text) for name, fn in zip(objective_names, objectives)}

            base = prompt
            best = base
            best_score = float("-inf")
            stale = 0
            prev_pool: List[str] = []

            for i in range(iterations):
                if loop.time() > deadline:
                    job.status = JobStatus.FAILED
                    job.result = {"error": "deadline_exceeded"}
                    await self._emit(job, "failed", job.result)
                    return
                mutants = mutate_prompt(base, settings.MAX_MUTATIONS_PER_ROUND, seed + i)
                recombos = recombine(prev_pool, recombination_rate, seed + i)
                candidates = [base] + mutants + recombos
                await self._emit(job, "mutation", {"count": len(mutants)})
                front = pareto_filter(candidates, n=settings.MAX_CANDIDATES, objectives=objectives)
                m = min(tournament_size * 2, len(front))
                if m > 1:
                    ranked = await tournament_rank(front[:m], task, tournament_size)
                else:
                    ranked = front
                chosen = ranked[0] if ranked else base
                det_scores = scores_for(chosen) if objective_names else {}
                judge = await judge_scores(task, chosen, examples, objective_names)
                progress = {
                    "iteration": i + 1,
                    "proposal": chosen,
                    "scores": {**det_scores, "judge": judge["scores"]},
                }
                await self._emit(job, "progress", progress)
                await self._emit(job, "selected", {"candidate": chosen, "scores": progress["scores"]})
                total = sum(det_scores.values()) + sum(judge["scores"].values())
                if total > best_score:
                    best_score = total
                    best = chosen
                    stale = 0
                else:
                    stale += 1
                    if stale >= early_stop_patience:
                        await self._emit(job, "early_stop", {"best": best})
                        break
                base = chosen
                prev_pool = ranked
                if loop.time() > deadline:
                    job.status = JobStatus.FAILED
                    job.result = {"error": "deadline_exceeded"}
                    await self._emit(job, "failed", job.result)
                    return
                await asyncio.sleep(0.05)

            det = scores_for(best) if objective_names else {}
            judge_final = await judge_scores(task, best, examples, objective_names)
            result_scores = (
                {**det, "judge": judge_final["scores"]}
                if objective_names
                else {"judge": judge_final["scores"]}
            )
            job.result = {"proposal": best, "lessons": [], "scores": result_scores}
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
