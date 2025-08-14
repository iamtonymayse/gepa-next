from __future__ import annotations

from typing import Dict, List

from ..settings import get_settings
from .judge import judge_pair
from .mutations import mutate_prompt
from .optimize_engine import pareto_filter
from .recombination import recombine


async def run_eval(
    store, base_prompt: str, target_model: str | None, seed: int, limits: dict, emit
):
    s = get_settings()
    max_ex = min(limits.get("max_examples") or s.EVAL_MAX_EXAMPLES, s.EVAL_MAX_EXAMPLES)
    examples = await store.list_examples(limit=max_ex, offset=0)
    task = base_prompt or (examples[0]["input"] if examples else "")
    await emit("eval_started", {"task": task, "examples": len(examples)})
    best = base_prompt
    patience = limits.get("early_stop_patience") or s.EARLY_STOP_PATIENCE
    stale = 0
    pool: List[str] = [base_prompt]
    for i, ex in enumerate(examples or []):
        muts = mutate_prompt(best, k=3, seed=seed + i)
        try:
            recs = recombine(
                pool,
                rate=limits.get("recombination_rate") or s.RECOMBINATION_RATE,
                seed=seed + i,
            )
        except Exception:
            recs = []
        cands = list({best, *muts, *recs})
        front = pareto_filter(cands, n=min(4, len(cands)))
        scores: Dict[str, int] = {}
        for c in front:
            res = await judge_pair(task, best, c, store=store)
            scores[c] = 1 if res["winner"] == "B" else 0
        sel = max(front, key=lambda c: scores.get(c, 0))
        improved = sel != best
        best = sel if improved else best
        pool = (pool + [sel])[-8:]
        await emit("eval_case", {"i": i, "selected": sel, "improved": improved})
        stale = 0 if improved else (stale + 1)
        if stale >= patience:
            await emit("early_stop", {"reason": "patience"})
            break
    await emit("eval_finished", {"best": best})
