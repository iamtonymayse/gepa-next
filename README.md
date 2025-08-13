# GEPA-NEXT
A GEPA-style evolutionary prompt optimization engine with GPT-5 judge.

## Docs
- **Quickstart:** `docs/QUICKSTART.md`
- **API Reference:** `docs/API.md`
- **SSE Guide:** `docs/SSE.md`
- **Auth (Bearer):** `docs/AUTH.md`
- **Environment (.env):** `docs/ENV.md`

## Highlights
- GPT-5 **judge** locked; **target** selectable per request.
- Idempotent job creation; SSE streaming with resume; bounded buffers/backpressure.
- Health/metrics/version endpoints for ops.

## Contributing
1) `pip install -e .[dev]`
2) `pytest -q`
3) Submit PRs with green tests.
