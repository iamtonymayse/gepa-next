# gepa-next

`gepa-next` is a FastAPI microservice template optimized for GitHub Codespaces. The goal is to provide rails for building production-ready Python services with minimal friction.

## Contribution guidelines

We welcome contributions! To contribute:

1. **Discuss first**: open an issue using the bug or feature templates to propose your change.
2. **Create a branch**: branch off of `main` using a descriptive name such as `feat/short-description` or `fix/bug-description`. For docs or housekeeping, use `docs/` or `chore/` prefixes.
3. **Install dependencies**: inside your Codespace run `uv sync` to install the exact locked dependencies.
4. **Run the quality gate**: execute `make qa` to run linting (ruff), formatting checks, type checking (mypy --strict), tests with coverage and security scans. All checks must pass locally.
5. **Keep secrets safe**: never commit secrets. Use Codespaces secrets for any sensitive values. Do not check in `.env` files with real credentials.
6. **Open a pull request**: push your branch and open a PR. Each PR must:
   - Pass all CI checks (lint, type check, tests with ≥80% coverage, security scans).
   - Receive at least one approving review.
   - Have a clear, descriptive title and summary.

Our main branch is protected: direct pushes are disabled. All changes must go through pull requests, CI must be green, and at least one review is required before merge.

For more details see [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md), and [SUPPORT.md](SUPPORT.md).

## Quickstart

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=dev
uvicorn innerloop.main:app --reload

# create a job (v1 API)
curl -s -X POST "http://127.0.0.1:8000/v1/optimize?iterations=1" -H "Idempotency-Key: demo-1"

# stream events
curl -N "http://127.0.0.1:8000/v1/optimize/<job_id>/events"

# resume a stream using Last-Event-ID
curl -N -H "Last-Event-ID: 5" "http://127.0.0.1:8000/v1/optimize/<job_id>/events"
```

### Python client

```python
import asyncio
from gepa_client import GepaClient

async def main():
    async with GepaClient("http://localhost:8000", openrouter_key="dev") as client:
        job_id = await client.create_job("hello world", idempotency_key="demo")
        async for env in client.stream(job_id):
            print(env.type)
            if env.type in {"finished", "failed", "cancelled"}:
                break

asyncio.run(main())
```

### TypeScript client

```ts
import { GepaClient } from 'gepa-client';

const client = new GepaClient('http://localhost:8000', { openrouterKey: 'dev' });
const jobId = await client.createJob('hello world');
for await (const env of client.stream(jobId)) {
  console.log(env.type);
  if (['finished', 'failed', 'cancelled'].includes(env.type)) break;
}
```

## Common errors

| Code | Fix |
| --- | --- |
| `unauthorized` | Provide a valid bearer token or set `OPENROUTER_API_KEY` |
| `not_found` | Verify the job ID |
| `rate_limited` | Slow down requests or increase quota |
| `payload_too_large` | Reduce request body size |
| `not_cancelable` | Job already finished or failed |
| `sse_backpressure` | Consume events faster |
| `validation_error` | Check request parameters |
| `internal_error` | Retry or contact support |
