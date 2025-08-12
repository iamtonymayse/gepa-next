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

# create a job
curl -s -X POST "http://127.0.0.1:8000/optimize?iterations=1"

# stream events
curl -N "http://127.0.0.1:8000/optimize/<job_id>/events"
```
