from __future__ import annotations

from typing import List, TypeVar

T = TypeVar("T")


def pareto_filter(items: List[T], n: int = 1) -> List[T]:
    return items[:n]
