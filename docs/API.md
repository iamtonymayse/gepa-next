# GEPA API Reference

## POST /v1/optimize
Create an optimization job.

### Query Parameters
- `iterations` (int, optional, default=`MAX_ITERATIONS` clamp): upper bound on evolution rounds.
- `last_event_id` (int, optional): for immediate replay before streaming (SSE path).

### Headers
- `Authorization: Bearer <token>` – required unless dev bypass is enabled.
- `Idempotency-Key` – string; maps to a persistent job ID for safe retries.

### JSON Body
- `prompt` (string, required): task spec.
- `target_model_id` (string, optional): overrides `TARGET_MODEL_DEFAULT`.
- `budget.max_generations` (int, optional): hard cap on total generations.
- `examples` (array, optional): seed shots, each `{input, output}`.
- `constraints` (object, optional): e.g., token caps or style hints.

### Responses
- `201`: `{"job_id": "...", "status": "started"}`
- `4xx/5xx`: uniform error envelope `{ "error": {"code": "...", "message": "..."} }`

## GET /v1/optimize/{job_id}
Fetch final state (or current snapshot).

## GET /v1/optimize/{job_id}/events
SSE stream of events. See `docs/SSE.md`.

## DELETE /v1/optimize/{job_id}
Cancel job.

## Admin
- `GET /v1/admin/jobs` – list
- `GET /v1/admin/jobs/{job_id}` – details
- `DELETE /v1/admin/jobs/{job_id}` – purge
- `POST /v1/admin/jobs/{job_id}/cancel` – cancel

## Health & Metrics
- `/v1/healthz`, `/v1/readyz`, `/v1/version`, `/v1/metricsz` (JSON), `/v1/metrics` (text)
