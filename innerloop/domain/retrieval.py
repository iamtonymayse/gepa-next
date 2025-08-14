from __future__ import annotations

import math
from typing import Any, Dict, List

from ..settings import get_settings

_idf: Dict[str, float] | None = None


def _tokenize(text: str) -> List[str]:
    return text.split()


def _build_idf(examples: List[Dict[str, Any]]) -> None:
    global _idf
    if _idf is not None:
        return
    df: Dict[str, int] = {}
    for ex in examples:
        tokens = set(_tokenize(ex.get("input", "") + " " + ex.get("expected", "")))
        for t in tokens:
            df[t] = df.get(t, 0) + 1
    total = max(1, len(examples))
    _idf = {t: math.log(total / (1 + c)) for t, c in df.items()}


async def retrieve(
    query: str, k: int, store: Any | None = None
) -> List[Dict[str, Any]]:
    k = max(0, min(k, get_settings().RETRIEVAL_MAX_EXAMPLES))
    examples: List[Dict[str, Any]] = []
    if store is not None:
        try:
            examples = await store.list_examples()
        except Exception:
            examples = []
    if not examples:
        return []
    _build_idf(examples)
    query_tokens = set(_tokenize(query))
    scores: List[tuple[float, Dict[str, Any]]] = []
    for ex in examples:
        ex_tokens = set(_tokenize(ex.get("input", "") + " " + ex.get("expected", "")))
        common = query_tokens & ex_tokens
        score = sum((_idf or {}).get(tok, 0.0) for tok in common)
        scores.append((score, ex))
    scores.sort(key=lambda t: t[0], reverse=True)
    top = [ex for sc, ex in scores if sc > 0.0][:k]
    if not top:
        return examples[:k]
    return top
