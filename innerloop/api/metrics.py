from __future__ import annotations

import time
from typing import Dict, Tuple, DefaultDict
from collections import defaultdict

# Simple counters used across the app (jobs, rate limiting, etc.)
_counters: Dict[str, int] = {
    "jobs_created": 0,
    "jobs_finished": 0,
    "jobs_failed": 0,
    "jobs_cancelled": 0,
    "sse_clients": 0,  # used as a gauge via +/- increments
    "rate_limited": 0,
    "oversize_rejected": 0,
}

# HTTP request metrics
_http_requests_total: DefaultDict[Tuple[str, str, int], int] = defaultdict(int)  # (method, path, status) -> count

# histogram buckets (seconds)
_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_http_hist_buckets: DefaultDict[Tuple[str, str, float], int] = defaultdict(int)  # (method, path, le) -> count
_http_hist_sum: DefaultDict[Tuple[str, str], float] = defaultdict(float)  # (method, path) -> sum
_http_hist_count: DefaultDict[Tuple[str, str], int] = defaultdict(int)  # (method, path) -> count


def inc(name: str, value: int = 1) -> None:
    _counters[name] = _counters.get(name, 0) + value


def record_http_request(*, method: str, path: str, status: int, duration_s: float) -> None:
    _http_requests_total[(method, path, status)] += 1
    key = (method, path)
    _http_hist_sum[key] += max(0.0, float(duration_s))
    _http_hist_count[key] += 1
    t = max(0.0, float(duration_s))
    placed = False
    for b in _BUCKETS:
        if t <= b:
            _http_hist_buckets[(method, path, b)] += 1
            placed = True
        else:
            # still need cumulative counts; fill later in exposition
            pass
    # +Inf bucket accounted for in exposition as count
    if not placed:
        # nothing to do; +Inf will cover it
        pass


def snapshot() -> Dict[str, float | int]:
    data: Dict[str, float | int] = {**_counters}
    data["ts"] = time.time()
    return data


def _labels(d: Dict[str, str]) -> str:
    items = ",".join(f'{k}="{v}"' for k, v in d.items())
    return f"{{{items}}}" if items else ""


def prometheus() -> str:
    lines: list[str] = []
    # http_requests_total
    lines.append("# HELP http_requests_total Total HTTP requests.")
    lines.append("# TYPE http_requests_total counter")
    for (method, path, status), count in sorted(_http_requests_total.items()):
        lines.append(
            f'http_requests_total{_labels({"method":method,"path":path,"status":str(status)})} {count}'
        )
    # http_request_duration_seconds
    lines.append("# HELP http_request_duration_seconds Request duration in seconds.")
    lines.append("# TYPE http_request_duration_seconds histogram")
    # prepare cumulative buckets per (method,path)
    raw: DefaultDict[Tuple[str, str, float], int] = defaultdict(int)
    for (method, path, le), count in _http_hist_buckets.items():
        raw[(method, path, le)] += count
    keys = {(m, p) for (m, p, _le) in raw.keys()} | set(_http_hist_count.keys())
    for (method, path) in sorted(keys):
        cum = 0
        for b in _BUCKETS:
            cum += raw.get((method, path, b), 0)
            lines.append(
                f'http_request_duration_seconds_bucket{_labels({"method":method,"path":path,"le":str(b)})} {cum}'
            )
        # +Inf bucket equals total count
        total = _http_hist_count.get((method, path), 0)
        lines.append(
            f'http_request_duration_seconds_bucket{_labels({"method":method,"path":path,"le":"+Inf"})} {total}'
        )
        s = _http_hist_sum.get((method, path), 0.0)
        lines.append(f'http_request_duration_seconds_sum{_labels({"method":method,"path":path})} {s}')
        lines.append(
            f'http_request_duration_seconds_count{_labels({"method":method,"path":path})} {total}'
        )
    # sse_clients gauge
    lines.append("# HELP sse_clients Number of connected SSE clients.")
    lines.append("# TYPE sse_clients gauge")
    lines.append(f"sse_clients {_counters.get('sse_clients', 0)}")
    # jobs_* counters
    for name in (
        "jobs_created",
        "jobs_finished",
        "jobs_failed",
        "jobs_cancelled",
        "rate_limited",
        "oversize_rejected",
    ):
        prom = f"{name}_total"
        lines.append(f"# TYPE {prom} counter")
        lines.append(f"{prom} {_counters.get(name, 0)}")
    return "\n".join(lines) + "\n"

