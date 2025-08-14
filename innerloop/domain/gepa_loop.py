from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, cast

from ..settings import get_settings
from .candidate import Candidate, apply_edits
from .engine import get_target_provider
from .eval import evaluate_batch
from .examples import load_pack
from .judge import judge_scores
from .operators import OPERATORS
from .optimize_engine import pareto_filter
from .reflection_multirole import update_lessons_journal
from .reflection_runner import run_reflection


def _shingles(text: str, k: int = 3) -> set[tuple[str, ...]]:
    toks = re.findall(r"\w+", text.lower())
    return set(tuple(toks[i : i + k]) for i in range(max(0, len(toks) - k + 1)))


def _max_jaccard_3gram(cand_text: str, others_texts: List[str]) -> float:
    s = _shingles(cand_text, 3)
    if not s:
        return 0.0
    best = 0.0
    for t in others_texts:
        o = _shingles(t, 3)
        if not o:
            continue
        inter = len(s & o)
        union = len(s | o)
        j = (inter / union) if union else 0.0
        if j > best:
            best = j
    return best


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
    population: List[Candidate] = [Candidate(id="seed", sections=[prompt], examples_subset=None, meta={})]
    lessons: List[str] = []
    frontier: List[Candidate] = []
    rollouts = 0
    best_score = None
    stagnation = 0
    for gen in range(max_gens):
        await emit(job, "generation_started", {"gen": gen, "population_size": len(population)})
        scored: List[Candidate] = []
        target_model = payload.get("target_model")
        examples_dicts = [{"input": ex.input, "expected": ex.output, **ex.meta} for ex in pack.examples]
        for cand in population:
            res = await evaluate_batch(
                provider,
                "\n".join(cand.sections),
                pack.examples,
                settings,
                model=target_model,
            )
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
            try:
                jres = await judge_scores(
                    prompt=str(payload.get("prompt", "")),
                    candidate="\n".join(cand.sections),
                    examples=examples_dicts,
                    objectives=None,
                )
                vals = list((jres.get("scores") or {}).values())
                cand.meta["judge_score"] = sum(vals) / (10.0 * len(vals)) if vals else 0.0
            except Exception:
                cand.meta["judge_score"] = 0.0
            await emit(
                job,
                "judge_scored",
                {"id": cand.id, "judge_score": cand.meta["judge_score"]},
            )
            scored.append(cand)
        all_texts = ["\n".join(c.sections) for c in scored]
        for i, cand in enumerate(scored):
            max_j = _max_jaccard_3gram(all_texts[i], all_texts[:i] + all_texts[i + 1 :])
            cand.meta["diversity"] = 1.0 - max_j
        objectives = [
            lambda c: -c.meta.get("score", 0.0),
            lambda c: c.meta.get("length", 0.0),
            lambda c: c.meta.get("cost", 0.0),
            lambda c: c.meta.get("latency", 0.0),
            lambda c: -c.meta.get("judge_score", 0.0),
            lambda c: -c.meta.get("diversity", 0.0),
        ]
        try:
            frontier = pareto_filter(scored, objectives=objectives, n=len(scored))
        except Exception:
            frontier = pareto_filter(scored, objectives=None, n=len(scored))
        frontier.sort(
            key=lambda c: (
                c.meta.get("judge_score", 0.0),
                c.meta.get("diversity", 0.0),
            ),
            reverse=True,
        )
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
        await emit(
            job,
            "selected",
            {
                "id": best.id,
                "meta": {
                    "judge_score": best.meta.get("judge_score"),
                    "diversity": best.meta.get("diversity"),
                    "score": best.meta.get("score"),
                },
            },
        )
        # === Multi-role reflection sequence ===
        await emit(job, "reflection_started", {"gen": gen})

        # Build a plain dict view of examples for prompts
        ex_dicts = [{"input": ex.input, "expected": ex.output, **ex.meta} for ex in pack.examples]
        base_text = "\n".join(best.sections)

        # Author drafts an improved prompt
        author = await run_reflection(
            base_text,
            "author",
            gen,
            examples=ex_dicts,
            target_model=payload.get("target_model") or settings.TARGET_MODEL_DEFAULT,
        )

        # Reviewer critiques the draft
        reviewer = await run_reflection(
            cast(str, author.get("proposal") or base_text),
            "reviewer",
            gen,
            examples=ex_dicts,
            target_model=payload.get("target_model") or settings.TARGET_MODEL_DEFAULT,
        )

        # Planner suggests concrete edits (we still keep edits in stub form)
        planner = await run_reflection(
            base_text,
            "planner",
            gen,
            examples=ex_dicts,
            target_model=payload.get("target_model") or settings.TARGET_MODEL_DEFAULT,
        )

        # Reviser applies the plan and produces final revised prompt; also returns edits
        revision = await run_reflection(
            base_text,
            "revision",
            gen,
            examples=ex_dicts,
            target_model=payload.get("target_model") or settings.TARGET_MODEL_DEFAULT,
        )

        # Merge lessons and stream update
        new_lessons: List[str] = []
        for r in (author, reviewer, planner, revision):
            new_lessons.extend(cast(List[str], r.get("lessons", [])))
        lessons = update_lessons_journal(lessons, new_lessons)
        await emit(job, "lessons_updated", {"count": len(lessons), "sample": lessons[:3]})

        # Apply revision edits to the best candidate to form next population seed
        edited = apply_edits(best, cast(Sequence[Dict[str, Any]], revision.get("edits", [])))

        await emit(job, "reflection_finished", {"gen": gen})

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
        "best_prompt": ("\n".join(frontier[0].sections) if frontier else payload.get("prompt", "")),
        "frontier": [{"id": c.id, "score": c.meta.get("score", 0.0)} for c in frontier],
        "lessons": lessons,
    }
