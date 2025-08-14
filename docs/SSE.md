# Server-Sent Events (SSE)

Endpoint: `GET /v1/optimize/{job_id}/events`
- Media type: `text/event-stream`
- Prelude: `retry: <ms>`
- Idle ping: `:\n\n`
- Terminals: `finished`, `failed`, `cancelled`
- Resume: `Last-Event-ID` header or `last_event_id` query.

## Event envelope
Each `data:` line is a compact JSON object with at least:
```json
{"id":5,"type":"progress","schema_version":1,"job_id":"123e4567","ts":1712345678,"data":{...}}
```

## HTTP/stream headers
The SSE endpoint sets:
- Content-Type: text/event-stream
- Cache-Control: no-cache
- Connection: keep-alive
- X-Accel-Buffering: no

## Heartbeats
Idle heartbeats are sent as `:\n\n` to keep intermediaries from closing the connection.

## Resume semantics
Clients may resume by sending `Last-Event-ID: <id>`. The server will attempt to replay from the next event id when possible and otherwise continue from the current head.

## Curl (live)
```bash
curl -N -H "Authorization: Bearer $API_BEARER_TOKEN" \
  "http://localhost:8000/v1/optimize/$JOB/events"
```

## Curl (resume from id=5)
```bash
curl -N -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Last-Event-ID: 5" \
  "http://localhost:8000/v1/optimize/$JOB/events"
```

## Python client (requests + sseclient-py)
See `examples/python_sse_client.py`.

## Node client (EventSource)
See `examples/node_sse_client.js`.

## Event types

- started – job acknowledged and beginning.
- mutation – a batch of candidate prompts was generated. `{ "count": <int> }`
- progress – an iteration checkpoint. Includes proposal, normalized scores, and improvement delta.
- selected – the current best candidate and a short list of top-k previews.
- finished – terminal event with final proposal, summary, and a reason.

### progress event shape

```
{
  "type": "progress",
  "schema_version": 1,
  "job_id": "123e4567",
  "ts": 1712345678,
  "id": 12,
  "data": {
    "iteration": 2,
    "proposal": "....",
    "target_model": "openai/gpt-5-mini",
    "rubric": "overall quality and clarity",
    "scores": {
      "composite": 0.71,
      "diversity": 0.23,
      "coverage": 0.44,
      "brevity": 0.90,
      "judge": {"brevity": 10, "diversity": 8, "coverage": 7}
    },
    "delta_best": 0.08
  }
}
```

### selected event shape

```
{
  "type": "selected",
  "schema_version": 1,
  "job_id": "123e4567",
  "ts": 1712345679,
  "id": 13,
  "data": {
    "candidate": "....",
    "scores": { "composite": 0.71, "judge": {"...": "..."} },
    "top_k": [
      { "composite": 0.71, "prompt_preview": "...." },
      { "composite": 0.65, "prompt_preview": "...." },
      { "composite": 0.60, "prompt_preview": "...." }
    ]
  }
}
```

### finished event shape

```
{
  "type": "finished",
  "schema_version": 1,
  "job_id": "123e4567",
  "ts": 1712345680,
  "id": 20,
  "data": {
    "proposal": "....",
    "lessons": ["...","..."],
    "scores": { "composite": 0.74 },
    "target_model": "openai/gpt-5-mini",
    "rubric": "overall quality and clarity",
    "reason": "max_iterations"
  }
}
```
