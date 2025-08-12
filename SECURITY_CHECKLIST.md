# Security Checklist

## Security Quick Start – Top 10
1. Require auth (`REQUIRE_AUTH`) and keep bearer tokens rotated.
2. Never log secrets; Authorization headers are redacted and request IDs added.
3. Enforce per-IP rate limiting on `POST /optimize`.
4. Drop requests with bodies over `MAX_REQUEST_BYTES` (~64 KB default).
5. Clamp job iterations to `MAX_ITERATIONS` to avoid runaway loops.
6. Limit SSE queue size (`SSE_QUEUE_MAXSIZE`) and fail after `SSE_BACKPRESSURE_FAIL_TIMEOUT_S`.
7. Serve over TLS via a trusted proxy; set strict headers for SSE and HTTP.
8. Disable CORS unless `CORS_ALLOWED_ORIGINS` is explicitly configured.
9. Keep dependencies pinned and run `pip-audit` regularly.
10. Purge finished/failed jobs via TTLs to minimize data retention.

## 1. Overview
**Checklist**
- Document threat model using STRIDE.
- Identify risks around SSE streaming, auth bypass, and background jobs.

**Why it matters**
Understanding attacker goals (spoofing, tampering, etc.) informs which controls matter most for this tiny service.

**How to verify**
- Review this file and design docs before major changes.

## 2. Authentication & Authorization
**Checklist**
- `REQUIRE_AUTH` defaults to true.
- Validate bearer tokens against `API_BEARER_TOKENS`.
- Allow bypass when `OPENROUTER_API_KEY` is set and no `Authorization` header is present.
- Support token rotation by loading tokens on startup only.

**Why it matters**
Prevents unauthorized job creation and keeps administrative backdoors auditable.

**How to verify**
- Code: [`innerloop/settings.py#L11-L21`](innerloop/settings.py#L11-L21), [`innerloop/api/middleware/auth.py`](innerloop/api/middleware/auth.py)
- Run: `pytest -q tests/test_security_perf.py::test_auth_matrix`

## 3. Token Handling
**Checklist**
- Never log raw tokens or API keys.
- Store secrets in environment variables only.
- Provide a rotation playbook.

**Why it matters**
Reduces blast radius if credentials leak and enables fast revocation.

**How to verify**
- Code: [`innerloop/api/middleware/logging.py`](innerloop/api/middleware/logging.py)
- Rotate: update `API_BEARER_TOKENS` env and restart process.

## 4. Input Validation & Limits
**Checklist**
- Clamp iterations to `MAX_ITERATIONS`.
- Enforce `MAX_REQUEST_BYTES` for POST/PUT/PATCH.
- Reject overly long query parameters.
- Disallow unknown JSON fields at API layer when used.

**Why it matters**
Stops resource exhaustion and unexpected code paths.

**How to verify**
- Code: [`innerloop/settings.py#L18-L21`](innerloop/settings.py#L18-L21), [`innerloop/api/middleware/limits.py`](innerloop/api/middleware/limits.py), [`innerloop/api/jobs/registry.py`](innerloop/api/jobs/registry.py)
- Run: `pytest -q tests/test_security_perf.py::test_request_size_limit`

## 5. Rate Limiting / DoS Resilience
**Checklist**
- Per-IP token bucket on `POST /optimize`.
- Bounded SSE queue (`SSE_QUEUE_MAXSIZE`).

**Why it matters**
Mitigates burst traffic and unbounded memory growth.

**How to verify**
- Code: [`innerloop/api/middleware/ratelimit.py`](innerloop/api/middleware/ratelimit.py), [`innerloop/settings.py#L15-L21`](innerloop/settings.py#L15-L21)
- Run: `pytest -q tests/test_security_perf.py::test_rate_limit`

## 6. Transport & Headers
**Checklist**
- TLS terminates at the proxy; internal app speaks HTTP.
- SSE responses set `Cache-Control: no-store`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
- Non-SSE routes set `X-Content-Type-Options: nosniff` (consider CSP/CSRF docs for API-only service).

**Why it matters**
Protects data in transit and prevents caching or MIME sniffing issues.

**How to verify**
- Code: [`innerloop/api/routers/optimize.py`](innerloop/api/routers/optimize.py)
- Run: `pytest -q tests/test_security_perf.py::test_sse_headers`

## 7. CORS
**Checklist**
- Only enable when `CORS_ALLOWED_ORIGINS` is non-empty.
- Warn when `*` is used in production.

**Why it matters**
Prevents unintended cross-origin access from browsers.

**How to verify**
- Code: [`innerloop/settings.py#L11-L21`](innerloop/settings.py#L11-L21), [`innerloop/main.py`](innerloop/main.py)

## 8. Secrets Management
**Checklist**
- Never commit secrets.
- Use env vars or secret stores.
- Document rotation procedure.

**Why it matters**
Keeps credentials out of version control and allows fast revocation.

**How to verify**
- Scan repo: `rg -i "api_key"` and ensure only in settings/tests.

## 9. Logging & Privacy
**Checklist**
- Strip PII; redact `Authorization` headers.
- Include `X-Request-ID` for correlation.

**Why it matters**
Ensures observability without leaking sensitive data.

**How to verify**
- Code: [`innerloop/api/middleware/logging.py`](innerloop/api/middleware/logging.py)
- Run: `pytest -q tests/test_security_perf.py::test_request_id_header`

## 10. Dependencies / Supply Chain
**Checklist**
- Pin dependency ranges in `requirements.txt`.
- Run `pip-audit` or `uv pip compile` regularly.

**Why it matters**
Limits exposure to vulnerable upstream packages.

**How to verify**
- Code: [`requirements.txt`](requirements.txt)
- Command: `pip-audit` (optional)

## 11. Observability / Incident Response
**Checklist**
- Correlate logs via request IDs.
- Alarm on error rates and job failures.
- Detect stalled SSE streams.

**Why it matters**
Speeds up investigation during outages or attacks.

**How to verify**
- Review monitoring dashboards; ensure request IDs appear in logs.

## 12. Data Retention
**Checklist**
- Expire job results using `JOB_TTL_*` settings.
- Document how TTLs enforce data minimization.

**Why it matters**
Minimizes stored data and reduces privacy liability.

**How to verify**
- Code: [`innerloop/settings.py#L22-L25`](innerloop/settings.py#L22-L25), [`innerloop/api/jobs/registry.py`](innerloop/api/jobs/registry.py)
