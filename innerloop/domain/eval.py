from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Dict, Sequence

from .examples import Example


@dataclass
class RolloutResult:
    scores_by_example: Dict[str, Dict[str, float]]
    mean_scores: Dict[str, float]
    traces: list[dict]
    cost: float
    latency: float
    cached: bool = False


_CACHE: Dict[str, RolloutResult] = {}


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def exact_match(pred: str, target: str) -> float:
    return 1.0 if _normalize(pred) == _normalize(target) else 0.0


def regex_pass(pred: str, pattern: str) -> float:
    import re

    return 1.0 if re.search(pattern, pred) else 0.0


async def evaluate_batch(
    provider,
    candidate_prompt: str,
    examples: Sequence[Example],
    settings,
    model: str | None = None,
) -> RolloutResult:
    key_src = candidate_prompt + "|".join(e.input + e.output for e in examples)
    key = hashlib.sha256(key_src.encode()).hexdigest()
    cached = _CACHE.get(key)
    if cached:
        cached.cached = True
        return cached
    scores: Dict[str, Dict[str, float]] = {}
    traces: list[dict] = []
    total = 0.0
    start = asyncio.get_event_loop().time()
    for ex in examples:
        prompt = f"{candidate_prompt} {ex.input}".strip()
        try:
            output = await provider.complete(
                prompt,
                model=model or getattr(settings, "TARGET_MODEL_DEFAULT", None),
            )
        except Exception:
            output = ""
        score = exact_match(output, ex.output)
        scores[ex.id] = {"exact_match": score}
        total += score
        traces.append({"example_id": ex.id, "prompt": prompt, "output": output})
    latency = asyncio.get_event_loop().time() - start
    mean = {"exact_match": total / len(examples) if examples else 0.0}
    result = RolloutResult(scores, mean, traces, cost=0.0, latency=latency)
    _CACHE[key] = result
    return result
