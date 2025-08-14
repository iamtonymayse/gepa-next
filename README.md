# gepa-next

GEPA-NEXT is a production-lean prompt optimization service that implements a GEPA-style evolutionary loop with streaming progress (SSE) and a fixed judge model. If you care about getting higher-quality prompts with fewer hand-tuned iterations, this is the reason this repo exists.

> Why GEPA?
The GEPA paper ("Guided Evolutionary Prompt Optimization") reports consistent gains over GRPO-style baselines in their experiments, thanks to (a) stronger selection using a fixed judge, (b) explicit lesson logging, and (c) diversity-preserving evolution. In short: less thrash, better prompts. See the deep-dive in docs/GEPA.md and the paper (arXiv:2507.19457) for details.

## Status
- HTTP API with /v1/optimize jobs, SSE progress stream, and health/metrics endpoints.
- Fixed judge model; request-selectable target model.
- Idempotent job creation; cancel & resume semantics.

## TL;DR — How GEPA works here
1. Start with an initial prompt and (optionally) example tasks.
2. Generate a population of candidate prompts via small, targeted edits.
3. Score candidates using a fixed judge model that compares outputs against goals/examples and emits structured feedback.
4. Select the best (quality × diversity), log lessons, and evolve.
5. Repeat for iterations, then return the champion + artifacts.

This service wires that loop into a clean API with server-sent events for real-time progress and artifacts for auditing.

## Quickstart

### Local, dev mode (auth bypass for POST /optimize)
```bash
python -m innerloop --dev
```

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/optimize?iterations=5" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -d '{
        "prompt": "You are an assistant that writes helpful answers.",
        "target_model_id": "openai/gpt-5-mini",
        "examples": [
          {"input": "Summarize benefits of containerization for a CTO.", "ideal":"A crisp, non-hype summary with ops trade-offs."}
        ]
      }'
```

Then stream progress:

```bash
curl -N "http://127.0.0.1:8000/v1/optimize/$JOB_ID/events" \
  -H "Authorization: Bearer ${API_TOKEN}"
```

Events are standard SSE. Example envelope:

```
data: {"id":5,"type":"progress","schema_version":1,"job_id":"123e4567","ts":1712345678,"data":{"stage":"select","iteration":2,"best_score":0.71}}
```

Supports `Last-Event-ID` for resume and sends periodic `:\n\n` heartbeats.

## Endpoints
- POST /v1/optimize — start an optimization job
- GET /v1/optimize/{job_id} — job state
- GET /v1/optimize/{job_id}/events — SSE stream of job events
- DELETE /v1/optimize/{job_id} — cancel
- GET /v1/examples / POST /v1/examples — manage example bank
- GET /v1/healthz — health check
- GET /v1/readyz — readiness check
- GET /v1/version — version info
- GET /v1/metricsz — JSON metrics
- GET /v1/metrics — Prometheus text metrics

## Auth
Set `API_BEARER_TOKENS=["token1","token2"]` in `.env` and send `Authorization: Bearer ${API_TOKEN}`.
Dev bypass for unauthenticated POST /optimize is enabled only with `python -m innerloop --dev` or `REQUIRE_AUTH=false`.

## Metrics
GET `/v1/metrics` exposes Prometheus-style text. `sse_clients` is a gauge; see also JSON at `/v1/metricsz`.

## Learn more
- GEPA deep-dive for this service: docs/GEPA.md
- API reference & envelopes: docs/API.md, docs/SSE.md
