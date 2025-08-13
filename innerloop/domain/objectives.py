from __future__ import annotations

from typing import Callable, List


def score_brevity(text: str) -> float:
    return -len(text)


def score_diversity(text: str) -> float:
    toks = text.lower().split()
    return len(set(toks)) / max(1, len(toks))


def score_coverage(text: str, examples: List[dict]) -> float:
    tokens: List[str] = []
    for ex in examples:
        tokens.extend(ex.get("input", "").lower().split())
    if not tokens:
        return 0.0
    example_set = set(tokens)
    text_set = set(text.lower().split())
    if not example_set:
        return 0.0
    return len(example_set & text_set) / len(example_set)


def get_objectives(names: List[str] | None, examples: List[dict] | None) -> List[Callable[[str], float]]:
    examples = examples or []
    funcs: List[Callable[[str], float]] = []
    for name in names or []:
        if name == "brevity":
            funcs.append(score_brevity)
        elif name == "diversity":
            funcs.append(score_diversity)
        elif name == "coverage":
            def cov_fn(text: str, _examples=examples):
                return score_coverage(text, _examples)
            funcs.append(cov_fn)
    return funcs
