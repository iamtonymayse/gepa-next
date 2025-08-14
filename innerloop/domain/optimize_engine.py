from __future__ import annotations

from typing import Callable, List, Sequence, TypeVar

from ..settings import get_settings
from .judge import get_judge, judge_pair
from .recombination import recombine

T = TypeVar("T")


def pareto_filter(
    items: Sequence[T],
    n: int = 1,
    objectives: Sequence[Callable[[T], float]] | None = None,
) -> List[T]:
    if not items:
        return []
    if objectives is None:
        if isinstance(items[0], str):
            objectives = [
                lambda s: len(str(s)),
                lambda s: -len(set(str(s).lower().split())),
            ]
        else:
            objectives = [
                lambda c: -getattr(c, "meta", {}).get("score", 0.0),
                lambda c: getattr(c, "meta", {}).get("length", 0.0),
                lambda c: getattr(c, "meta", {}).get("cost", 0.0),
                lambda c: getattr(c, "meta", {}).get("latency", 0.0),
            ]
    scored: List[tuple[T, tuple[float, ...]]] = [
        (item, tuple(obj(item) for obj in objectives)) for item in items
    ]
    front: List[tuple[T, tuple[float, ...]]] = []
    for i, (item_i, score_i) in enumerate(scored):
        dominated = False
        for j, (item_j, score_j) in enumerate(scored):
            if i == j:
                continue
            if all(a <= b for a, b in zip(score_j, score_i)) and any(
                a < b for a, b in zip(score_j, score_i)
            ):
                dominated = True
                break
        if not dominated:
            front.append((item_i, score_i))
    front.sort(key=lambda t: (t[1], str(t[0])))
    return [item for item, _ in front[:n]]


async def tournament_rank(cands: List[str], task: str, k: int) -> List[str]:
    if k < 2 or len(cands) < 2:
        return list(cands)
    pool = list(cands)
    while len(pool) > 1:
        next_round: List[str] = []
        for i in range(0, len(pool), k):
            group = pool[i : i + k]
            champ = group[0]
            for challenger in group[1:]:
                res = await judge_pair(task, champ, challenger)
                champ = res.get("winner", champ)
            next_round.append(champ)
        pool = next_round
    champion = pool[0]
    rest = [c for c in cands if c != champion]
    return [champion] + rest


async def rank_candidates(
    items: List[str],
    objectives: List[Callable[[str], float]] | None,
    task: str,
    tournament_size: int,
    n: int = 1,
) -> List[str]:
    front = pareto_filter(items, n=n, objectives=objectives)
    top = front[: min(len(front), max(1, tournament_size * 2))]
    if len(top) > 1:
        try:
            ordered = await tournament_rank(top, task, tournament_size)
            return ordered[:n]
        except Exception:
            return top[:n]
    return top[:n]


async def pareto_v2(
    *,
    prompt: str,
    proposals: Sequence[T],
    n: int = 1,
    rubric: str | None = None,
) -> List[T]:
    """Judge-driven selection using configured judge with fallback."""
    if not proposals:
        return []
    try:
        judge = get_judge(get_settings())
        ranked = await judge.rank(
            prompt=prompt,
            proposals=[str(p) for p in proposals],
            rubric=rubric,
        )
        ordered = [p for p, _ in ranked]
        mapping = {str(p): p for p in proposals}
        return [mapping[o] for o in ordered[:n] if o in mapping]
    except Exception:
        return pareto_filter(proposals, n=n)


__all__ = [
    "pareto_filter",
    "tournament_rank",
    "rank_candidates",
    "recombine",
    "pareto_v2",
]
