from __future__ import annotations

from typing import Callable, List, Sequence, TypeVar

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
    front.sort(key=lambda t: t[1])
    return [item for item, _ in front[:n]]
