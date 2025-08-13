from __future__ import annotations

import asyncio
import hashlib
from typing import Dict, List

from ..settings import get_settings
from .engine import get_target_provider


async def run_reflection(
    prompt: str,
    mode: str,
    iteration: int,
    *,
    examples: List[dict] | None = None,
    target_model_id: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Dict[str, object]:
    settings = get_settings()
    if settings.USE_MODEL_STUB:
        await asyncio.sleep(0.01)
        parts = [prompt, str(iteration)]
        for ex in (examples or [])[:2]:
            hashed = hashlib.sha256(ex.get("input", "").encode()).hexdigest()[:8]
            parts.append(hashed)
        proposal = " | ".join(parts)
    else:
        provider = get_target_provider(settings)
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
            for ex in examples[:2]:
                inp = ex.get("input", "")
                exp = ex.get("expected")
                messages.append({"role": "user", "content": inp})
                if exp:
                    messages.append({"role": "assistant", "content": exp})
        messages.append({"role": "user", "content": prompt})
        proposal = await provider.complete(
            prompt,
            messages=messages,
            model=target_model_id or settings.TARGET_DEFAULT_MODEL_ID,
            temperature=temperature,
            max_tokens=max_tokens,
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
