-Production-lean prompt optimization service implementing GEPA-style evolution with SSE streaming, idempotent jobs, and a fixed GPT-5 judge.

-## Endpoints

– POST /v1/optimize — start an optimization job
– GET  /v1/optimize/{job_id} — job state
– GET  /v1/optimize/{job_id}/events — SSE stream of job events
– DELETE /v1/optimize/{job_id} — cancel
– GET  /v1/examples / POST /v1/examples — manage example bank
– GET  /v1/healthz — health check
– GET  /v1/metricsz — metrics (JSON)
– GET  /v1/metrics — metrics (text/plain)

-## Admin Endpoints
– GET /v1/admin/jobs
– GET /v1/admin/jobs/{job_id}
– DELETE /v1/admin/jobs/{job_id}
– POST /v1/admin/jobs/{job_id}/cancel

-## SSE Streaming & Resume
-The events endpoint is Server-Sent Events (text/event-stream) with:
– Prelude retry: <ms> sent first.
– Idle pings :\n\n when no events are pending.
– Terminal types: finished, failed, cancelled.
– Resume using the Last-Event-ID header or last_event_id query param.

-Resume example:
-```bash
-curl -N \
	•	-H “Authorization: Bearer ” \
	•	-H “Last-Event-ID: 5” \
	•	“http://localhost:8000/v1/optimize/<job_id>/events”
-```
	•	

-## Judge vs Target
-Judge (fixed): Hard-locked to openai:gpt-5-judge via settings; cannot be overridden via API.
-Target (per-call): Select with target_model_id in the request. If omitted, server uses TARGET_MODEL_DEFAULT.
-Providers are chosen per model; the judge runs via OpenRouter with OpenAI pass-through headers.

-## Example Session (copy-paste)

-```bash
-# Start a job
-curl -s -H “Authorization: Bearer $API_TOKEN” \
	•	-H “Content-Type: application/json” \
	•	-d ‘{“prompt”:“Summarize: …”,“mode”:“gepa”,“target_model_id”:“openai:gpt-4o-mini”,“budget”:{“max_generations”:2}}’ \
	•	http://localhost:8000/v1/optimize | tee /tmp/job.json
	•	

-JOB=$(jq -r .job_id /tmp/job.json)

-# Stream events (SSE)
-curl -N -H “Authorization: Bearer $API_TOKEN” \
	•	-H “Accept: text/event-stream” \
	•	http://localhost:8000/v1/optimize/$JOB/events
	•	

-# Query state
-curl -s -H “Authorization: Bearer $API_TOKEN” \
	•	http://localhost:8000/v1/optimize/$JOB | jq .
	•	

-# Metrics (text)
-curl -s http://localhost:8000/v1/metrics | head -n 20
-```
-=======
-A GEPA-style evolutionary prompt optimization engine with GPT-5 judge.

-## Docs
– Quickstart: docs/QUICKSTART.md
– API Reference: docs/API.md
– SSE Guide: docs/SSE.md
– Auth (Bearer): docs/AUTH.md
– Environment (.env): docs/ENV.md

-## Highlights
– GPT-5 judge locked; target selectable per request.
– Idempotent job creation; SSE streaming with resume; bounded buffers/backpressure.
– Health/metrics/version endpoints for ops.

-## Contributing
-1) pip install -e .[dev]
-2) pytest -q
-3) Submit PRs with green tests.
->>>>>>> main
+# GEPA-NEXT
+
+Production-ready GEPA-style evolutionary prompt optimization service with SSE streaming, idempotent jobs, bounded buffers/backpressure, and a fixed GPT-5 judge.
+
+## Docs
+- Quickstart: docs/QUICKSTART.md
+- API Reference: docs/API.md
+- SSE Guide: docs/SSE.md
+- Auth (Bearer): docs/AUTH.md
+- Environment (.env): docs/ENV.md
+
+## Endpoints
+- POST /v1/optimize — start an optimization job
+- GET  /v1/optimize/{job_id} — job state
+- GET  /v1/optimize/{job_id}/events — SSE stream of job events
+- DELETE /v1/optimize/{job_id} — cancel
+- GET /v1/examples / POST /v1/examples — manage example bank
+- GET /v1/healthz — health check
+- GET /v1/readyz — readiness check
+- GET /v1/version — version info
+- GET /v1/metricsz — metrics (JSON)
+- GET /v1/metrics — metrics (text/plain)
+
+## Admin Endpoints
+- GET /v1/admin/jobs
+- GET /v1/admin/jobs/{job_id}
+- DELETE /v1/admin/jobs/{job_id}
+- POST /v1/admin/jobs/{job_id}/cancel
+
+## SSE Streaming & Resume
+The events endpoint is Server-Sent Events (text/event-stream) with:
+- Prelude retry: <ms> sent first.
+- Idle pings :\n\n when no events are pending.
+- Terminal types: finished, failed, cancelled.
+- Resume using the Last-Event-ID header or last_event_id query param.
+
+Resume example:
+```bash
+curl -N \
	•	-H “Authorization: Bearer ” \
	•	-H “Last-Event-ID: 5” \
	•	“http://localhost:8000/v1/optimize/<job_id>/events”
+```
	•	

+## Judge vs Target
+Judge (fixed): Hard-locked to openai:gpt-5-judge via settings; cannot be overridden via API.
+Target (per-call): Select with target_model_id in the request. If omitted, server uses TARGET_MODEL_DEFAULT.
+Providers are chosen per model; the judge runs via OpenRouter with OpenAI pass-through headers.
+
+## Example Session (copy-paste)
+```bash
+# Start a job
+curl -s -H “Authorization: Bearer $API_BEARER_TOKEN” \
	•	-H “Content-Type: application/json” \
	•	-d ‘{“prompt”:“Summarize: …”,“mode”:“gepa”,“target_model_id”:“openai:gpt-4o-mini”,“budget”:{“max_generations”:2}}’ \
	•	http://localhost:8000/v1/optimize | tee /tmp/job.json
	•	

+JOB=$(jq -r .job_id /tmp/job.json)
+
+# Stream events (SSE)
+curl -N -H “Authorization: Bearer $API_BEARER_TOKEN” \
	•	-H “Accept: text/event-stream” \
	•	http://localhost:8000/v1/optimize/$JOB/events
	•	

+# Query state
+curl -s -H “Authorization: Bearer $API_BEARER_TOKEN” \
	•	http://localhost:8000/v1/optimize/$JOB | jq .
	•	

+# Metrics (text)
+curl -s http://localhost:8000/v1/metrics | head -n 20
+```
+
+## Highlights
+- GPT-5 judge locked; target selectable per request.
+- Idempotent job creation; SSE streaming with resume; bounded buffers/backpressure.
+- Health/metrics/version endpoints for ops.
+
+## Contributing
+1) pip install -e .[dev]
+2) `pytest -q`
+3) Submit PRs with green tests.