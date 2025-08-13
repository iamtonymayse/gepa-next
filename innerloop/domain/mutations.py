from __future__ import annotations
from typing import List
import random


def _swap_words(text: str, rnd: random.Random) -> str:
    words = text.split()
    if len(words) < 2:
        return text
    i, j = rnd.sample(range(len(words)), 2)
    words[i], words[j] = words[j], words[i]
    return " ".join(words)


def _drop_word(text: str, rnd: random.Random) -> str:
    words = text.split()
    if not words:
        return text
    idx = rnd.randrange(len(words))
    return " ".join(w for i, w in enumerate(words) if i != idx)


def _reverse(text: str, rnd: random.Random) -> str:
    return " ".join(reversed(text.split()))


_OPERATORS = [_swap_words, _drop_word, _reverse]


def mutate_prompt(base: str, k: int, seed: int) -> List[str]:
    rnd = random.Random(seed)
    out: List[str] = []
    for i in range(k):
        op = _OPERATORS[i % len(_OPERATORS)]
        mutated = op(base, rnd)
        if mutated and mutated not in out and mutated != base:
            out.append(mutated)
    return out
