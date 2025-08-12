from __future__ import annotations

import asyncio
from typing import Dict

from ..settings import get_settings
from .engine import get_provider_from_env


async def run_reflection(prompt: str, mode: str, iteration: int) -> Dict[str, object]:
    settings = get_settings()
    if settings.USE_MODEL_STUB:
        await asyncio.sleep(0.01)
        proposal = f"proposal {iteration}"
    else:
        provider = get_provider_from_env()
        proposal = await provider.complete(prompt)
    return {
        "mode": mode,
        "summary": f"summary {iteration}",
        "proposal": proposal,
        "lessons": f"lessons {iteration}",
        "meta": {"iteration": iteration},
    }
