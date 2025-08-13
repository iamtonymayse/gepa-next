GEPA-NEXT — Developer Usage Guide (v1)

Guided Evolutionary Prompt Architect (GEPA) — a small FastAPI service that runs optimize jobs and streams live progress via Server-Sent Events (SSE). This guide shows what the API is for, how to use it confidently, and the exact wire protocol you can rely on.

⸻

TL;DR (golden path)

# 0) run the server (dev)
export OPENROUTER_API_KEY=dev   # enables /optimize POST bypass without Authorization
uvicorn innerloop.main:app --reload

# 1) create a job (idempotent)
curl -s -X POST "http://localhost:8000/v1/optimize?iterations=2" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-123" \
  -d '{"prompt":"rewrite this text crisply","context":{"tone":"succinct"}}'
# => {"job_id":"<uuid>"}

# 2) stream live events (SSE; auto-retry hinted by server)
curl -N "http://localhost:8000/v1/optimize/<job_id>/events"

# 3) (optional) resume from last event
curl -N "http://localhost:8000/v1/optimize/<job_id>/events" \
  -H "Last-Event-ID: 7"

# 4) inspect job state or cancel
curl -s "http://localhost:8000/v1/optimize/<job_id>"
curl -s -X DELETE "http://localhost:8000/v1/optimize/<job_id>"


⸻

What this API is for
	•	Create a short-lived “optimize” job that iterates on a prompt/idea.
	•	Stream progress in real time as SSE events: started, mutation, progress, selected, early_stop, and a terminal event (finished, failed, cancelled, or shutdown).
	•	Resume a stream after a disconnect using Last-Event-ID without losing data.
	•	Persist jobs (optional sqlite store) so you can replay terminal events after a restart.
	•	Operate safely: bearer auth by default, idempotency keys, per-request size cap, and basic rate limits.

⸻

Versioning & stability
	•	Public surface lives under /v1/*.
Unversioned routes may exist temporarily and will include a Deprecation header pointing to the v1 path.
	•	Event schema is versioned with schema_version: 1 in every SSE data payload.

⸻

Authentication
	•	Default: Bearer token required for all routes except /v1/healthz and /v1/readyz.

Authorization: Bearer <token>

Tokens are configured via API_BEARER_TOKENS.

	•	Bypass (dev/test convenience): If OPENROUTER_API_KEY is set and the request omits Authorization,
POST /v1/optimize (or /optimize) is allowed. All other routes (including GET /v1/optimize/{id}, SSE /v1/optimize/{id}/events, and DELETE /v1/optimize/{id}) still require auth.
	•	CORS: Disabled by default unless you set CORS_ALLOWED_ORIGINS.

⸻

Endpoints (v1)

Method	Path	Purpose
GET	/v1/healthz	Liveness probe: {"status":"ok"}
GET	/v1/readyz	Readiness probe: {"status":"ready"}
POST	/v1/optimize?iterations=<int>	Create a job; headers: Idempotency-Key optional
GET	/v1/optimize/{job_id}	Fetch job state {job_id,status,created_at,updated_at,result}
DELETE	/v1/optimize/{job_id}	Cancel a running job (terminal cancelled)
GET	/v1/optimize/{job_id}/events	SSE stream; supports Last-Event-ID/?last_event_id= resume
GET	/v1/admin/jobs	(Admin) List recent jobs (auth required; no bypass)
DELETE	/v1/admin/jobs/{job_id}	(Admin) Hard-delete a job (auth required; no bypass)
GET	/metricsz	(Ops) JSON snapshot counters (auth may be required)

⚠️ Terminal events: the stream always ends with one of finished|failed|cancelled|shutdown.

⸻

Requests & responses

Create a job

Request

POST /v1/optimize?iterations=1
Content-Type: application/json
Authorization: Bearer <token>     # or rely on bypass for /optimize only
Idempotency-Key: <any-stable-id>  # optional but recommended

{
  "prompt": "rewrite this text crisply",
  "context": { "tone": "succinct" }
}

	•	iterations clamped to 1..MAX_ITERATIONS (configurable).
	•	If the same Idempotency-Key is reused within IDEMPOTENCY_TTL_S, the same job_id is returned and no new job is created.

Response

{ "job_id": "7a2f0a5b-6b91-4ad2-b1c3-44f9f8..." }

Examples & Objectives
You can supply inline examples and specify scoring objectives:

```
{
  "prompt": "summarize",
  "examples": [
    {"input": "long text", "expected": "short"},
    {"input": "another"}
  ],
  "objectives": ["brevity", "diversity", "coverage"]
}
```

Model parameters
Optional knobs per request:

```
{
  "seed": 123,
  "model_id": "gpt-4o-mini",
  "temperature": 0.2,
  "max_tokens": 100,
  "tournament_size": 4,
  "recombination_rate": 0.5,
  "early_stop_patience": 3
}
```

Judge vs Target model
- **Judge**: fixed by server (`JUDGE_MODEL_ID`, default GPT-5). Clients cannot choose it.
- **Judge caching & rate limits**: pairwise comparisons use an internal GPT-5 judge with LRU caching and a token-bucket limiter (`JUDGE_QPS_MAX`).
- **BYO OpenAI key**: set `OPENAI_API_KEY` on the server to pass through as `X-OpenAI-Api-Key` to OpenRouter.
- **Target model**: choose per request with `target_model_id`; if omitted, server uses `TARGET_MODEL_DEFAULT`.

Examples CRUD
- `POST /v1/examples/bulk` – upsert examples in bulk
- `GET /v1/examples` – list examples with pagination
- `DELETE /v1/examples/{id}` – remove an example

Evaluation jobs
- `POST /v1/eval/start` with body `{ name, target_model_id?, max_examples?, seed?, tournament_size?, recombination_rate?, early_stop_patience? }`
- `GET /v1/eval/{job_id}/events` – stream `started`, `eval_started`, `eval_case`, optional `early_stop`, `eval_finished`, and terminal `finished`
- Judge model is fixed via `JUDGE_MODEL_ID` in settings; target model may be provided per request

Full request with examples and objectives:
```json
{
  "prompt": "summarize",
  "examples": [
    {"input": "long text", "expected": "short"},
    {"input": "another"}
  ],
  "objectives": ["brevity", "diversity", "coverage"],
  "target_model_id": "gpt-4o-mini"
}
```

Additional event types: `mutation` (counts generated mutations), `selected` (top candidate per round), and `early_stop` (loop terminated early but job still finishes).

Sample progress event (SSE):
```
data: {
  "type": "progress",
  "data": {
    "proposal": "...",
    "scores": {
      "brevity": -5.0,
      "diversity": 0.2,
      "judge": {"brevity": 7, "diversity": 6, "coverage": 5}
    }
  }
}
```

Scores in SSE payloads
Progress and terminal events may include objective scores:

```
data: {
  "type": "progress",
  "data": {
    "proposal": "...",
    "scores": {"brevity": -10.0, "diversity": 0.5}
  }
}
```

Wall-time deadline
Each job has a hard limit (MAX_WALL_TIME_S). Exceeding it results in
`{"error":"deadline_exceeded"}`.

⸻

Job state

GET /v1/optimize/{job_id}

{
  "job_id": "...",
  "status": "running",
  "created_at": 1722033640.12,
  "updated_at": 1722033641.55,
  "result": null
}


⸻

Cancel

DELETE /v1/optimize/{job_id}

	•	If running → transitions to cancelled and emits terminal event.
	•	If already terminal → 409 { "error": { "code": "not_cancelable", ... } }.
	•	If unknown → 404.

⸻

SSE streaming — exact contract

Request

GET /v1/optimize/{job_id}/events?last_event_id=<int>   # optional
# or header:
Last-Event-ID: <int>

Response headers

Content-Type: text/event-stream
Cache-Control: no-store
Connection: keep-alive
X-Accel-Buffering: no

Prelude (first line always)

retry: <SSE_RETRY_MS>

Events
Each event is 2–4 lines separated by \n; a blank line terminates the event:

id: 8
event: progress
data: {"type":"progress","schema_version":1,"job_id":"...","ts":1722033641.11,"data":{"iteration":1,"summary":"...","proposal":"..."}}

	•	id: monotonic per job (used to resume).
	•	event: is one of: started, progress, finished, failed, cancelled, shutdown.
	•	data: is a JSON envelope:

{
  "type": "progress",
  "schema_version": 1,
  "job_id": "7a2f0a5b-...",
  "ts": 1722033641.11,
  "id": 8,
  "data": {
    "iteration": 1,
    "summary": "Iteration 1 summary for '...'",
    "proposal": "Proposal v1 for '...'"
  }
}

Idle ping: the server sends an SSE comment to keep connections alive when there’s nothing to send:

:

Terminal: the final event ends the stream:

event: finished
data: {"type":"finished",...}

Backpressure: if a client stops reading and the per-job queue overflows or times out, the job may fail with:

event: failed
data: {"type":"failed","data":{"error":"sse_backpressure"}}


⸻

Error model (HTTP & SSE)

Errors return a uniform shape:

{
  "error": {
    "code": "unauthorized",   // enum
    "message": "Unauthorized",
    "details": {}
  }
}

Codes you may see

Code	When it occurs
unauthorized	Missing/invalid bearer token; bypass not applicable
not_found	Unknown job id
not_cancelable	Cancelling a job that’s already terminal
payload_too_large	Request exceeds MAX_REQUEST_BYTES
rate_limited	Token/IP exceeded rate limits
validation_error	Malformed JSON or invalid field value
sse_backpressure	Client not reading; queue overflow timing out
internal_error	Unexpected server error (logged with request id)


⸻

Settings (env) & defaults

All settings are pydantic-settings v2 backed; lists can be comma-separated strings.

Variable	Default	Purpose
REQUIRE_AUTH	true	Enforce bearer auth by default
API_BEARER_TOKENS	[]	Comma-sep tokens: token1,token2
OPENROUTER_API_KEY	unset	Enables /v1/optimize POST bypass when set and no Authorization header
CORS_ALLOWED_ORIGINS	[]	Enable CORS for given origins
SSE_RETRY_MS	1500	Suggested client retry backoff
SSE_PING_INTERVAL_S	1.0	Idle ping cadence
SSE_QUEUE_MAXSIZE	100	Per-job event queue bound
SSE_BUFFER_SIZE	200	Ring buffer kept per job for resume
SSE_BACKPRESSURE_FAIL_TIMEOUT_S	2 × ping	Fail job if .put() blocks this long
MAX_ITERATIONS	10	Upper bound for iterations
MAX_REQUEST_BYTES	65536	Request size cap (413 if exceeded)
RATE_LIMIT_PER_MIN	60	Token/IP budget per minute
RATE_LIMIT_BURST	30	Allowed burst above steady rate
JOB_STORE	memory	memory or sqlite
SQLITE_PATH	gepa.db	SQLite file when JOB_STORE=sqlite
IDEMPOTENCY_TTL_S	600	Idempotency key lifetime
JOB_REAPER_INTERVAL_S	2.0	Reaper sweep cadence
JOB_TTL_FINISHED_S	30	Auto-delete finished jobs after
JOB_TTL_FAILED_S	120	Auto-delete failed jobs after
JOB_TTL_CANCELLED_S	60	Auto-delete cancelled jobs after
USE_MODEL_STUB	true	Use local stub provider (no network)
SERVICE_NAME	gepa-next	Title for OpenAPI/UI
SERVICE_ENV	dev	Environment tag


⸻

Security & rate limiting
	•	Auth runs before rate limiting and request size checks.
	•	Rate limits apply per bearer token; bypassed POSTs are tracked under a synthetic “anonymous-openrouter” principal.
	•	Request size limits apply to all write methods (POST/PUT/PATCH); SSE GET is exempt.

⸻

Persistence & idempotency
	•	Memory store (default): fast, ephemeral.
	•	SQLite store: set JOB_STORE=sqlite, SQLITE_PATH=/path/to/db.
Jobs and events persist across restarts; replay uses the stored event ring.
	•	Idempotency: server stores {Idempotency-Key → job_id} for IDEMPOTENCY_TTL_S. Reusing the same key returns the same job_id (no duplicate work).

⸻

Observability
        •       Logging: one structured line per request (method, path, status, duration ms, request id, client IP, job id when present). Authorization is redacted.
        •       Metrics:
                - **Prometheus**: `/v1/metrics` with `http_requests_total`, `http_request_duration_seconds` (histogram), `sse_clients` gauge, and job counters (e.g., `jobs_created_total`).
                - JSON snapshot: `/v1/metricsz` (unchanged).

⸻

Examples

cURL (with idempotency & resume)

JOB_ID=$(curl -s -X POST "http://localhost:8000/v1/optimize?iterations=2" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-123" \
  -d '{"prompt":"summarize this","context":{"audience":"cto"}}' | jq -r .job_id)

# initial stream
curl -N "http://localhost:8000/v1/optimize/$JOB_ID/events" | tee /tmp/stream.log

# grab last id, resume
LAST_ID=$(grep -E '^id:' /tmp/stream.log | tail -1 | cut -d' ' -f2)
curl -N "http://localhost:8000/v1/optimize/$JOB_ID/events" -H "Last-Event-ID: $LAST_ID"

Python (async, httpx)

import anyio, httpx, json

BASE = "http://localhost:8000"
async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        # create
        r = await client.post("/v1/optimize?iterations=2",
            headers={"Idempotency-Key":"py-demo-1"},
            json={"prompt":"tighten this paragraph","context":{"tone":"direct"}})
        r.raise_for_status()
        job_id = r.json()["job_id"]

        last_id = None
        # stream (handle resume if disconnected)
        while True:
            headers = {}
            if last_id is not None:
                headers["Last-Event-ID"] = str(last_id)
            async with client.stream("GET", f"/v1/optimize/{job_id}/events", headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if not line:  # event boundary
                        continue
                    if line.startswith("id:"):
                        last_id = int(line.split(":",1)[1].strip())
                    elif line.startswith("event:"):
                        ev = line.split(":",1)[1].strip()
                        if ev in {"finished","failed","cancelled","shutdown"}:
                            return
                    elif line.startswith("data:"):
                        envelope = json.loads(line[5:].strip())
                        print("event:", envelope["type"], "data:", envelope["data"])
            # simple backoff before resuming
            await anyio.sleep(1.0)

anyio.run(main)

JavaScript (browser EventSource)

<script>
const JOB_ID = "<uuid>";
const src = new EventSource(`/v1/optimize/${JOB_ID}/events`, { withCredentials: false });

src.onopen = () => console.log('SSE open');
src.addEventListener('started', e => console.log('started', JSON.parse(e.data)));
src.addEventListener('progress', e => console.log('progress', JSON.parse(e.data)));
src.addEventListener('finished', e => { console.log('finished', JSON.parse(e.data)); src.close(); });
src.onerror = (err) => console.warn('SSE error', err); // browser will auto-retry using "retry:" hint
</script>


⸻

Troubleshooting

Symptom	Likely cause / fix
401 unauthorized	Missing/invalid bearer token and bypass not active. Set Authorization: Bearer <token> or OPENROUTER_API_KEY (bypass applies to /v1/optimize only and only when no Authorization header is sent).
404 not_found	Wrong job_id.
409 not_cancelable	Job already terminal when DELETE was called.
429 rate_limited	You exceeded RATE_LIMIT_PER_MIN / BURST. Wait for Retry-After and try again.
413 payload_too_large	Body exceeds MAX_REQUEST_BYTES.
SSE connects but never starts	Ensure you kept the first line retry: <ms> and are not buffering (proxies must allow streaming; server sets X-Accel-Buffering: no).
Stream stops mid-run	Your client disconnected; resume using Last-Event-ID or ?last_event_id=.
sse_backpressure failure	Your client isn’t reading; consume events promptly or lower iteration rate.


⸻

Operational tips
	•	Run with uvicorn (dev): uvicorn innerloop.main:app --reload
	•	Production: multiple workers via a process manager; consider proxy timeouts ≥ 60s; keep-alive on; disable proxy buffering for SSE.
	•	SQLite: prefer journal_mode=WAL (the store sets sensible defaults).
	•	Metrics: scrape /metricsz and alert on error ratios or long tail latencies.

⸻

Appendix: Pydantic models (v1)

class OptimizeRequest(BaseModel):
    prompt: str
    context: Dict[str, Any] | None = None

class OptimizeResponse(BaseModel):
    job_id: str

class JobState(BaseModel):
    job_id: str
    status: Literal["pending","running","finished","failed","cancelled"]
    created_at: float
    updated_at: float
    result: Dict[str, Any] | None = None

class SSEEnvelope(BaseModel):
    type: Literal["started","progress","finished","failed","cancelled","shutdown"]
    schema_version: int = 1
    job_id: str
    ts: float
    id: int | None = None
    data: Dict[str, Any]

## GEPA mode

Set `mode` to `gepa` and supply a dataset pack to run the evolutionary loop.

```
curl -s -X POST "http://localhost:8000/v1/optimize" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"answer:","mode":"gepa","dataset":{"name":"toy_qa"},"budget":{"max_generations":2}}'
```

The SSE stream will include additional events: `generation_started`,
`candidate_scored`, `frontier_updated`, `lessons_updated` and
`budget_progress`. The terminal `finished` event contains the best_prompt.
