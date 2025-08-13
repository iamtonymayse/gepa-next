from __future__ import annotations

import asyncio
import json
import time
from functools import lru_cache
from typing import Any, Dict, List

from .engine import get_judge_provider
from ..settings import get_settings


def _build_judge_prompt(
    prompt: str,
    candidate: str,
    examples: List[dict] | None,
    objectives: List[str] | None,
) -> str:
    obj_list = ", ".join(objectives or [])
    parts = [
        "You are a strict judge. Score the candidate answer for each objective (0-10).",
        'Return JSON: {"scores":{...},"rationale":"..."}.',
        f"Objectives: {obj_list if obj_list else 'brevity, diversity, coverage'}.",
        f"Prompt: {prompt}",
        f"Candidate: {candidate}",
    ]
    if examples:
        ex_str = "; ".join(
            f"input: {e.get('input')}, expected: {e.get('expected', '')}" for e in examples
        )
        parts.append(f"Examples: {ex_str}.")
        parts.append(
            "Coverage should reflect how well candidate addresses prompt and examples."
        )
    return "\n".join(parts)


async def judge_scores(
    prompt: str,
    candidate: str,
    examples: List[dict] | None,
    objectives: List[str] | None,
) -> Dict[str, Any]:
    settings = get_settings()
    provider = get_judge_provider(settings)
    objectives = objectives or []
    if settings.USE_MODEL_STUB:
        words = candidate.split()
        uniq = set(words)
        brevity = 10 - (len(candidate) % 10)
        diversity = int(10 * (len(uniq) / len(words))) if words else 0
        ref_tokens = set(prompt.split())
        for ex in examples or []:
            ref_tokens.update(str(ex.get("input", "")).split())
            ref_tokens.update(str(ex.get("expected", "")).split())
        overlap = len(ref_tokens & set(words))
        coverage = int(10 * overlap / max(1, len(ref_tokens)))
        return {
            "scores": {
                "brevity": max(0, min(10, brevity)),
                "diversity": max(0, min(10, diversity)),
                "coverage": max(0, min(10, coverage)),
            },
            "rationale": "stub",
        }
    else:
        message = _build_judge_prompt(prompt, candidate, examples, objectives)
        raw = await provider.complete(
            message,
            model=settings.JUDGE_MODEL_ID,
            temperature=0.0,
            max_tokens=300,
        )
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
        scores: Dict[str, float] = {}
        for obj in objectives:
            try:
                val = float(data.get("scores", {}).get(obj, 0.0))
            except Exception:
                val = 0.0
            scores[obj] = max(0.0, min(10.0, val))
        rationale = data.get("rationale") or ""
        return {"scores": scores, "rationale": rationale}


CALLS = 0
_last = 0.0
_tokens = 1.0


def _norm_pair(task: str, a: str, b: str) -> tuple[str, str, str]:
    return (task or "",) + tuple(sorted([a or "", b or ""]))


def _cache_size() -> int:
    s = get_settings()
    return s.JUDGE_CACHE_SIZE if not s.USE_MODEL_STUB else 1024


@lru_cache(maxsize=1024)
def _stub_cache(task: str, a: str, b: str) -> Dict[str, Any]:
    global CALLS
    CALLS += 1
    winner = a if len(a) >= len(b) else b
    return {"winner": winner, "confidence": 1.0}


async def _rate_limit() -> None:
    global _tokens, _last
    s = get_settings()
    now = time.monotonic()
    _tokens = min(1.0, _tokens + (now - _last) * (s.JUDGE_QPS_MAX / 1.0))
    _last = now
    if _tokens < 1.0:
        await asyncio.sleep((1.0 - _tokens) / (s.JUDGE_QPS_MAX or 1.0))
        _tokens = 1.0


async def judge_pair(prompt_a: str, prompt_b: str, task: str) -> Dict[str, Any]:
    await _rate_limit()
    settings = get_settings()
    key = _norm_pair(task, prompt_a, prompt_b)
    if settings.USE_MODEL_STUB:
        return _stub_cache(*key)
    global CALLS
    if key in _non_stub_cache:
        return _non_stub_cache[key]
    CALLS += 1
    provider = get_judge_provider(settings)
    prompt = f"Task: {task}\nA: {prompt_a}\nB: {prompt_b}\nWhich is better? Reply A or B"
    raw = await provider.complete(
        prompt,
        model=settings.JUDGE_MODEL_ID,
        temperature=0.0,
        max_tokens=1,
    )
    winner = prompt_a if "A" in raw else prompt_b
    res = {"winner": winner, "confidence": 1.0}
    _non_stub_cache[key] = res
    if len(_non_stub_cache) > _cache_size():
        _non_stub_cache.pop(next(iter(_non_stub_cache)))
    return res


_non_stub_cache: Dict[tuple[str, str, str], Dict[str, Any]] = {}


async def judge_score(prompt: str, candidate: str, examples: List[dict] | None, objectives: List[str] | None) -> float:
    res = await judge_scores(prompt, candidate, examples, objectives)
    return float(sum(res.get("scores", {}).values()))
