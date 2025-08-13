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
    model_params: Dict[str, object] | None = None,
) -> Dict[str, object]:
    settings = get_settings()
    model_params = model_params or {}
    if settings.USE_MODEL_STUB:
        await asyncio.sleep(0.01)
        parts = [prompt]
        for ex in (examples or [])[:2]:
            parts.append(ex.get("input", ""))
        proposal = " | ".join(parts + [str(iteration)])
    else:
        provider = get_provider_from_env(settings)
        if model_params.get("model_id"):
            settings.MODEL_ID = str(model_params["model_id"])
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are GEPA reflection role = {mode}. "
                    "Optimize proposal with constraints and lessons. Output only the proposal text."
                ),
            }
        ]
        if examples:
            for ex in examples:
                inp = ex.get("input", "")
                exp = ex.get("expected")
                messages.append({"role": "user", "content": inp})
                if exp:
                    messages.append({"role": "assistant", "content": exp})
        messages.append({"role": "user", "content": prompt})
        proposal = await provider.complete(
            prompt,
            messages=messages,
            temperature=model_params.get("temperature"),
            max_tokens=model_params.get("max_tokens"),
        )
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
