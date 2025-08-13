from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Iterable, Tuple

from .engine import get_judge_provider, get_provider_from_env
from ..settings import get_settings, Settings
from .judge_prompts import PAIRWISE_TEMPLATE


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
_tokens = 1.0
_last = 0.0


def _norm(task: str, a: str, b: str) -> tuple[str, str, str]:
    x = (a or "").strip()
    y = (b or "").strip()
    if x <= y:
        return (task or "", x, y)
    else:
        return (task or "", y, x)


async def _throttle():
    s = get_settings()
    global _tokens, _last
    now = time.monotonic()
    _tokens = min(1.0, _tokens + (now - _last) * (s.JUDGE_QPS_MAX or 1.0))
    _last = now
    if _tokens < 1.0:
        await asyncio.sleep((1.0 - _tokens) / max(1e-6, s.JUDGE_QPS_MAX))
        _tokens = 1.0


async def judge_pair(task: str, a: str, b: str, store=None) -> Dict[str, Any]:
    global CALLS
    key = _norm(task, a, b)
    if store:
        cached = await store.get_judge_cached(*key)
        if cached:
            return cached
    s = get_settings()
    if s.USE_MODEL_STUB:
        CALLS += 1
        winner = "A" if (len(a), a) <= (len(b), b) else "B"
        res = {"winner": winner, "confidence": 0.7, "justification": "stub"}
    else:
        await _throttle()
        CALLS += 1
        provider = get_provider_from_env(s)
        prompt = PAIRWISE_TEMPLATE.format(task=task, a=a, b=b)
        out = await provider.complete(prompt, model=s.JUDGE_MODEL_ID)
        try:
            res = json.loads(out.strip())
        except Exception:
            res = {"winner": "A", "confidence": 0.5, "justification": "parse-fallback"}
    if store:
        confidence_val: Any = res.get("confidence", 0.5)
        try:
            confidence = float(confidence_val)
        except (TypeError, ValueError):
            confidence = 0.5
        await store.set_judge_cached(*key, res["winner"], confidence)
    return res


async def judge_score(prompt: str, candidate: str, examples: List[dict] | None, objectives: List[str] | None) -> float:
    res = await judge_scores(prompt, candidate, examples, objectives)
    return float(sum(res.get("scores", {}).values()))


# ---------------------------------------------------------------------------
# Lightweight judge interface for tests and simple usage


class JudgeStub:
    """Deterministic, offline judge for tests and local development."""

    async def score(
        self, *, prompt: str, proposal: str, rubric: str | None = None
    ) -> float:
        toks = proposal.lower().split()
        uniq = len(set(toks))
        return max(0.0, 100.0 - len(proposal)) + uniq

    async def rank(
        self, *, prompt: str, proposals: Iterable[str], rubric: str | None = None
    ) -> List[Tuple[str, float]]:
        items = [
            (p, await self.score(prompt=prompt, proposal=p, rubric=rubric))
            for p in proposals
        ]
        items.sort(key=lambda t: t[1], reverse=True)
        return items


def get_judge(settings: Settings | None = None):
    s = settings or get_settings()
    if s.USE_JUDGE_STUB or s.JUDGE_PROVIDER == "stub":
        return JudgeStub()
    # Fallback to stub if no external judge configured
    return JudgeStub()
