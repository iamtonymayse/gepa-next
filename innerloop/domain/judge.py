from __future__ import annotations

import json
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
