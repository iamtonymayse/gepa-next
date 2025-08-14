# Environment & .env Guide

Copy `.env.example` to `.env` and edit values:

```bash
cp .env.example .env
```

Key vars:
- `LOG_LEVEL` (`DEBUG|INFO|WARNING|ERROR`) – verbosity.
- `DEBUG_LOG_CONSOLE` (`true|false`) – force console logging.
- `API_BEARER_TOKENS` – JSON list of bearer tokens. Send `Authorization: Bearer ${API_TOKEN}`.
- `HOST` – interface to bind; defaults to 127.0.0.1 (loopback).
- `PORT` – port to bind; defaults to 8000.
- `TARGET_MODEL_DEFAULT` – default target model when request omits `target_model_id`.
- `JUDGE_MODEL_ID` – judge identifier (fixed in code to GPT-5 judge).
- `OPENROUTER_API_KEY` – required for judge/provider calls.
- `MAX_ITERATIONS` – cap for the GEPA loop.
- `SSE_BUFFER_SIZE`, `SSE_BACKPRESSURE_FAIL_TIMEOUT_S` – SSE buffering/backpressure.
- `CORS_ALLOWED_ORIGINS` – JSON list of allowed origins.

> Production note: a real auth system is planned. The single bearer token is for dev.
