# GEPA-NEXT

Production-lean prompt optimization service implementing GEPA-style evolution with SSE streaming, idempotent jobs, and a fixed GPT-5 judge.

## Endpoints

- POST /v1/optimize — start an optimization job
- GET  /v1/optimize/{job_id} — job state
- GET  /v1/optimize/{job_id}/events — SSE stream of job events
- DELETE /v1/optimize/{job_id} — cancel
- GET  /v1/examples / POST /v1/examples — manage example bank
- GET  /v1/healthz — health check
- GET  /v1/metricsz — metrics (JSON)
- GET  /v1/metrics — metrics (text/plain)

## SSE Contract

- Response Content-Type: text/event-stream
- Server prelude includes `retry: <ms>`; idle pings are sent as a single `:` line followed by a blank line.
- Clients may resume by sending `Last-Event-ID: <event_id>` or `?last_event_id=` query param.
- Terminal events are one of: `finished`, `failed`, `cancelled`.

## Judge vs Target

- **Judge**: fixed at `openai:gpt-5-judge` (configured via settings). The judge model is not overrideable via API.
- **Target**: selected per request via `OptimizeRequest.target_model_id`. If omitted, the service uses the default target model from settings.
- **Providers**: Judge uses OpenRouter with OpenAI pass-through; target uses the configured provider for the chosen model.

## Example Session (copy-paste)

```bash
# Start a job
curl -s -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Summarize: …","mode":"gepa","target_model_id":"openai:gpt-4o-mini","budget":{"max_generations":2}}' \
  http://localhost:8000/v1/optimize | tee /tmp/job.json

JOB=$(jq -r .job_id /tmp/job.json)

# Stream events (SSE)
curl -N -H "Authorization: Bearer $API_TOKEN" \
  -H "Accept: text/event-stream" \
  http://localhost:8000/v1/optimize/$JOB/events

# Query state
curl -s -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/v1/optimize/$JOB | jq .

# Metrics (text)
curl -s http://localhost:8000/v1/metrics | head -n 20
```
