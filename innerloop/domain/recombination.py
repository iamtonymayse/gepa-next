from __future__ import annotations
from typing import List, Tuple
import random


def crossover(a: str, b: str, seed: int) -> str:
    rnd = random.Random(seed)  # nosec B311
    sa, sb = a.split(), b.split()
    if not sa or not sb:
        return a or b
    cut_a, cut_b = rnd.randrange(1, len(sa)), rnd.randrange(1, len(sb))
    child = " ".join(sa[:cut_a] + sb[cut_b:])
    return child


def recombine(pool: List[str], rate: float, seed: int) -> List[str]:
    if rate <= 0.0 or len(pool) < 2:
        return []
    rnd = random.Random(seed)  # nosec B311
    out: List[str] = []
    pairs: List[Tuple[str, str]] = []
    for _ in range(max(1, int(len(pool) * rate))):
        a, b = rnd.sample(pool, 2)
        pairs.append((a, b))
    for i, (a, b) in enumerate(pairs):
        out.append(crossover(a, b, seed + i))
    return out
