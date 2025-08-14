from __future__ import annotations

import difflib
from typing import Iterable, List, Tuple


def normalized_edit_distance(a: str, b: str) -> float:
    """Return normalized edit distance in [0,1] where 0==identical."""
    if a == b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a or "", b or "").ratio()
    return max(0.0, min(1.0, 1.0 - ratio))


def dedupe_and_filter(
    base: str, candidates: Iterable[str], min_delta: float = 0.05
) -> List[Tuple[str, float]]:
    """Drop exact duplicates and candidates too similar to *base*.

    Returns a list of ``(candidate, delta)`` pairs meeting ``min_delta``.
    """
    seen: set[str] = set()
    out: List[Tuple[str, float]] = []
    base_str = base or ""
    for c in candidates:
        c_norm = (c or "").strip()
        if not c_norm:
            continue
        if c_norm in seen:
            continue
        seen.add(c_norm)
        delta = normalized_edit_distance(base_str, c_norm)
        if delta >= min_delta:
            out.append((c_norm, delta))
    return out
