from __future__ import annotations

import asyncio
from typing import Dict


async def run_reflection(prompt: str, mode: str, iteration: int) -> Dict[str, object]:
    await asyncio.sleep(0.01)
    return {
        "mode": mode,
        "summary": f"summary {iteration}",
        "proposal": f"proposal {iteration}",
        "lessons": f"lessons {iteration}",
        "meta": {"iteration": iteration},
    }
