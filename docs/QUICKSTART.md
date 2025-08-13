# Quickstart (Local Dev)

## 1) Prereqs
- Python 3.11+
- `uvicorn`, `pip`, `venv`

## 2) Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

## 3) Configure
```bash
cp .env.example .env
${EDITOR:-vi} .env   # set OPENROUTER_API_KEY and API_BEARER_TOKEN at minimum
```

## 4) Run
```bash
uvicorn innerloop.main:app --host 0.0.0.0 --port 8000 --reload
```

Health:
```bash
curl -s localhost:8000/v1/healthz
curl -s localhost:8000/v1/version
```

## 5) First optimization (idempotent)
```bash
curl -s -X POST "http://localhost:8000/v1/optimize?iterations=2" \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Idempotency-Key: demo-1" -H "Content-Type: application/json" \
  -d '{"prompt":"Write a haiku about gravity.","target_model_id":"openai:gpt-4o-mini"}'
```

## 6) Stream events (SSE)
See `docs/SSE.md` for details and example clients in `examples/`.
