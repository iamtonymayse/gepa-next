from __future__ import annotations

import bisect
import time
from typing import Dict, List

_counters: Dict[str, int] = {
    "jobs_created": 0,
    "jobs_finished": 0,
    "jobs_failed": 0,
    "jobs_cancelled": 0,
    "sse_clients": 0,
    "rate_limited": 0,
    "oversize_rejected": 0,
    "judge_failures": 0,
}

_hist: Dict[str, List[float]] = {}


def inc(name: str, value: int = 1) -> None:
    _counters[name] = _counters.get(name, 0) + value


def observe(name: str, value: float) -> None:
    arr = _hist.setdefault(name, [])
    bisect.insort(arr, float(value))


def _pct(arr: List[float], p: float) -> float:
    if not arr:
        return 0.0
    idx = max(0, min(len(arr) - 1, int(round((p / 100.0) * (len(arr) - 1)))))
    return arr[idx]


def snapshot() -> Dict[str, float | int | dict]:
    data: Dict[str, float | int | dict] = {**_counters}
    data["ts"] = time.time()
    out: Dict[str, dict] = {}
    for k, arr in _hist.items():
        out[k] = {
            "count": len(arr),
            "p50": _pct(arr, 50),
            "p95": _pct(arr, 95),
            "p99": _pct(arr, 99),
        }
    data["histograms"] = out
    return data


def snapshot_metrics_json() -> Dict[str, float | int | dict]:
    """Return metrics snapshot suitable for JSON serialization."""
    return snapshot()


def snapshot_metrics_text() -> str:
    """Render metrics in a Prometheus-style text exposition format."""
    data = snapshot()
    lines: List[str] = []
    for key, value in data.items():
        if isinstance(value, (int, float)):
            lines.append(f"# HELP {key} {key}")
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {value}")
    return "\n".join(lines) + "\n"
