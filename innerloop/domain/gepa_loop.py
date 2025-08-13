from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, cast

from ..settings import get_settings
from .candidate import Candidate, apply_edits
from .engine import get_target_provider
from .eval import evaluate_batch
from .examples import load_pack
from .operators import OPERATORS
from .optimize_engine import pareto_filter
from .reflection_runner import run_reflection
from .reflection_multirole import update_lessons_journal


@dataclass
class Budget:
    max_rollouts: int | None = None
    max_generations: int | None = None
    max_cost: float | None = None


async def gepa_loop(job, emit, payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    provider = get_target_provider(settings)
    dataset = cast(Dict[str, Any], payload.get("dataset", {"name": "toy_qa"}))
    pack = load_pack(str(dataset.get("name", "toy_qa")))
    budget = Budget(**cast(Dict[str, Any], payload.get("budget", {})))
    max_gens = budget.max_generations or 1
    prompt = str(payload.get("prompt", ""))
    population: List[Candidate] = [
        Candidate(id="seed", sections=[prompt], examples_subset=None, meta={})
    ]
    lessons: List[str] = []
    frontier: List[Candidate] = []
    rollouts = 0
    best_score = None
    stagnation = 0
    for gen in range(max_gens):
        await emit(job, "generation_started", {"gen": gen, "population_size": len(population)})
        scored: List[Candidate] = []
        for cand in population:
            res = await evaluate_batch(provider, "\n".join(cand.sections), pack.examples, settings)
            rollouts += 1
            cand.meta.update(
                score=res.mean_scores.get("exact_match", 0.0),
                cost=res.cost,
                latency=res.latency,
                length=len("\n".join(cand.sections)),
            )
            await emit(
                job,
                "candidate_scored",
                {
                    "candidate_id": cand.id,
                    "score": cand.meta["score"],
                    "cost": cand.meta["cost"],
                    "len": cand.meta["length"],
                },
            )
            scored.append(cand)
        frontier = pareto_filter(scored, objectives=None, n=len(scored))
        best = frontier[0]
        await emit(
            job,
            "frontier_updated",
            {
                "gen": gen,
                "size": len(frontier),
                "best": {
                    "score": best.meta.get("score", 0.0),
                    "cost": best.meta.get("cost", 0.0),
                    "len": best.meta.get("length", 0.0),
                },
            },
        )
        refl: Dict[str, Any] = await run_reflection(
            "", "gepa", gen, examples=None
        )
        lessons = update_lessons_journal(lessons, cast(List[str], refl.get("lessons", [])))
        await emit(job, "lessons_updated", {"count": len(lessons), "sample": lessons[:3]})
        edited = apply_edits(best, cast(Sequence[Dict[str, Any]], refl.get("edits", [])))
        rng = random.Random(gen)  # nosec B311
        mutated = OPERATORS["reorder_sections"](edited, rng=rng)
        population = [mutated]
        await emit(job, "budget_progress", {"rollouts": rollouts})
        if budget.max_rollouts and rollouts >= budget.max_rollouts:
            break
        if best_score is None or best.meta["score"] > best_score:
            best_score = best.meta["score"]
            stagnation = 0
        else:
            stagnation += 1
        if stagnation >= 2:
            break
    return {
        "best_prompt": "\n".join(frontier[0].sections) if frontier else payload.get("prompt", ""),
        "frontier": [
            {"id": c.id, "score": c.meta.get("score", 0.0)} for c in frontier
        ],
    }
