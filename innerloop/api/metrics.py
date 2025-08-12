from __future__ import annotations

import time
from typing import Dict

_counters: Dict[str, int] = {
    "jobs_created": 0,
    "jobs_finished": 0,
    "jobs_failed": 0,
    "jobs_cancelled": 0,
    "sse_clients": 0,
    "rate_limited": 0,
    "oversize_rejected": 0,
}


def inc(name: str, value: int = 1) -> None:
    _counters[name] = _counters.get(name, 0) + value


def snapshot() -> Dict[str, float | int]:
    data: Dict[str, float | int] = {**_counters}
    data["ts"] = time.time()
    return data

