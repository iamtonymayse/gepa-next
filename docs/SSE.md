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
{"id":5,"type":"progress","ts":1712345678,"payload":{...}}
```

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
