# Performance Checklist

## Performance Quick Start – Top 10
1. Run with `uvicorn --http h11 --loop uvloop` (if available).
2. Use appropriate worker count: `workers = CPU cores` for CPU-bound, more for I/O.
3. Keep requests under `MAX_REQUEST_BYTES` (~64 KB default).
4. Enforce per-IP rate limiting on `POST /optimize`.
5. Avoid blocking calls; use `asyncio` all the way.
6. SSE queues are bounded; jobs fail after `SSE_BACKPRESSURE_FAIL_TIMEOUT_S`.
7. JSON serialization uses compact separators; consider `orjson` for heavy loads.
8. Track request/stream latencies with structured logs.
9. Load-test with `hey` or `wrk` before release.
10. Expire jobs via TTL to cap memory usage.
11. Resume SSE streams via `Last-Event-ID`; size buffers with `SSE_BUFFER_SIZE`.
12. Use Idempotency-Key headers to avoid duplicate jobs.
13. Enforce CI with ruff, mypy, and pytest on every change.
14. Prefer versioned APIs under `/v1` and plan deprecations for unversioned routes.
15. Persist jobs with `JOB_STORE=sqlite` (WAL); default `memory` trades durability for speed.
16. LocalEcho is the default model provider; set `USE_MODEL_STUB=false` and `OPENROUTER_API_KEY` for OpenRouter.
17. Pareto v1 ranks proposals by length and unique token count for deterministic results.

## 1. Process Model & Server
**Checklist**
- Prefer `uvicorn --http h11 --loop uvloop` (if uvloop installed).
- Tune worker count based on CPU cores and workload.
- Adjust keep-alive and proxy timeouts for expected SSE durations.

**Why it matters**
Optimal server flags reduce latency and prevent connection churn during long streams.

**How to verify**
- Command: `uvicorn innerloop.main:app --http h11 --loop uvloop`.

## 2. Async I/O Discipline
**Checklist**
- No blocking calls; use `asyncio.sleep` only for brief SSE flushes.
- Use bounded `asyncio.Queue` (`SSE_QUEUE_MAXSIZE`) for backpressure.

**Why it matters**
Blocking the event loop stalls all clients; bounded queues avoid unbounded memory use.

**How to verify**
- Code: [`innerloop/api/jobs/registry.py`](innerloop/api/jobs/registry.py)
- Run lint/static checks for blocking calls.

## 3. SSE-Specific Tuning
**Checklist**
- `retry:` value controlled by `SSE_RETRY_MS`.
- Ping interval via `SSE_PING_INTERVAL_S` to keep connections alive.
- Disable compression and buffering for SSE.

**Why it matters**
Stable streams reduce reconnects and ensure timely delivery.

**How to verify**
- Code: [`innerloop/settings.py#L15-L21`](innerloop/settings.py#L15-L21), [`innerloop/api/routers/optimize.py`](innerloop/api/routers/optimize.py)
- Manual: observe headers via `curl -i`.

## 4. Serialization & Payloads
**Checklist**
- Use compact JSON (`separators=(',', ':')`).
- Consider `orjson` for heavy workloads (optional).

**Why it matters**
Smaller payloads mean less bandwidth and CPU.

**How to verify**
- Code: [`innerloop/api/routers/optimize.py`](innerloop/api/routers/optimize.py)
- Benchmark serialization if needed.

## 5. Memory & Lifecycle
**Checklist**
- Jobs stored in registry with TTLs (`JOB_TTL_*`).
- Keep job objects lean; avoid storing large payloads.
- Periodic reaper removes old jobs.

**Why it matters**
Prevents memory leaks and keeps steady-state footprint predictable.

**How to verify**
- Code: [`innerloop/settings.py#L22-L25`](innerloop/settings.py#L22-L25), [`innerloop/api/jobs/registry.py`](innerloop/api/jobs/registry.py)
- Monitor process memory under load.

## 6. Rate limiting & Request limits
**Checklist**
- `MAX_REQUEST_BYTES` guards large payloads.
- Token bucket rate limiting via `RATE_LIMIT_OPTIMIZE_*`.

**Why it matters**
Protects service from overload by large or excessive requests.

**How to verify**
- Code: [`innerloop/api/middleware/limits.py`](innerloop/api/middleware/limits.py), [`innerloop/api/middleware/ratelimit.py`](innerloop/api/middleware/ratelimit.py)
- Run: `pytest -q tests/test_security_perf.py::test_rate_limit`

## 7. Profiling / Load-testing Playbook
**Checklist**
- Use `hey`/`wrk` for load tests (100–1000 SSE clients).
- Simulate long-lived streams and short bursts.

**Why it matters**
Exposes bottlenecks before production traffic does.

**How to verify**
- Command: `hey -n 100 -c 20 http://localhost:8000/healthz`
- Observe CPU/memory metrics during soak.

## 8. Observability
**Checklist**
- Log method, path, status, duration, request ID.
- Export counters for requests and SSE events (future work).

**Why it matters**
Metrics drive capacity planning and alerting.

**How to verify**
- Code: [`innerloop/api/middleware/logging.py`](innerloop/api/middleware/logging.py)
- Tail logs and confirm fields.

## 9. Capacity Planning
**Checklist**
- Estimate memory per job/client to size instances.
- Relate concurrency to `SSE_QUEUE_MAXSIZE` and TTLs.

**Why it matters**
Prevents overcommit and provides headroom for bursts.

**How to verify**
- Rough math: `concurrency * (job_size + queue_size) < available_ram`.
