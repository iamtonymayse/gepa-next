from __future__ import annotations

import asyncio
from typing import Dict, List

from ..settings import get_settings
from .engine import get_provider_from_env


async def run_reflection(
    prompt: str,
    mode: str,
    iteration: int,
    *,
    examples: List[dict] | None = None,
    target_model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Dict[str, object]:
    settings = get_settings()
    if settings.USE_MODEL_STUB:
        # Determinism reduces timing jitter for perf tests
        if not bool(settings.GEPA_DETERMINISTIC):
            await asyncio.sleep(0.01)
        proposal = f"proposal {iteration}"
    else:
        provider = get_provider_from_env(settings)
        proposal = await provider.complete(prompt)
    lessons = [f"lesson {iteration}"]
    edits = [{"op": "reorder_sections", "args": {}, "seed": iteration}]
    return {
        "mode": mode,
        "summary": f"summary {iteration}",
        "proposal": proposal,
        "lessons": lessons,
        "diagnoses": [],
        "edits": edits,
        "meta": {"iteration": iteration},
    }
