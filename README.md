# GEPA-NEXT — Guided Evolutionary Prompt Optimizer (beta)

Production-lean, research-backed prompt optimization. GEPA-NEXT implements the Guided Evolutionary Prompt Optimization loop with a fixed judge model, diversity-aware selection, a lessons journal, and real-time SSE progress — behind a clean HTTP API.

Why GEPA vs “just GRPO”?
The GEPA approach (arXiv:2507.19457) reports consistent gains over GRPO-style baselines by combining a fixed judge for stable scoring, lesson logging to compound improvements, and diversity-preserving selection to avoid premature convergence. Translation: less thrash, better prompts.
<!-- Badges -->

<!-- Tests badge — works only AFTER the workflow file exists on the default branch (main). -->
[![Tests](https://img.shields.io/github/actions/workflow/status/iamtonymayse/gepa-next/test-python.yml?branch=main&label=tests)](https://github.com/iamtonymayse/gepa-next/actions/workflows/test-python.yml)

<!-- If you’re seeing “repo or workflow not found”, it means the workflow file isn’t on main yet.
     Option A: merge the workflow to main.
     Option B (temporary): use a static placeholder badge until merge, then swap back. -->
<!-- [![Tests](https://img.shields.io/badge/tests-pending-lightgrey)](#) -->

<!-- Optional: Formatting workflow badge -->
[![Formatting](https://img.shields.io/github/actions/workflow/status/iamtonymayse/gepa-next/format.yml?branch=main&label=format)](https://github.com/iamtonymayse/gepa-next/actions/workflows/format.yml)

<!-- Release + License -->
[![Release](https://img.shields.io/github/v/release/iamtonymayse/gepa-next?include_prereleases&sort=semver)](https://github.com/iamtonymayse/gepa-next/releases)
[![License](https://img.shields.io/github/license/iamtonymayse/gepa-next)](https://github.com/iamtonymayse/gepa-next/blob/main/LICENSE)

<!-- Runtime/tooling -->
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/built%20with-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)

<!-- Linters & QA -->
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-46A9FC)](https://github.com/astral-sh/ruff)
[![isort](https://img.shields.io/badge/imports-isort-ef8336)](https://pycqa.github.io/isort/)
[![mypy](https://img.shields.io/badge/types-mypy-2A6DB2)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Bandit](https://img.shields.io/badge/security-bandit-EE3A3A)](https://bandit.readthedocs.io/)
[![Semgrep](https://img.shields.io/badge/security-semgrep-1B5E20)](https://semgrep.dev/)
[![gitleaks](https://img.shields.io/badge/secrets-gitleaks-8A2BE2)](https://github.com/gitleaks/gitleaks)

<!-- “Made with …” (pick one or show both) -->
[![Made with Codex](https://img.shields.io/badge/made%20with-Codex-000000?logo=openai&logoColor=white)](#)
[![Made with GPT-5](https://img.shields.io/badge/made%20with-GPT%E2%80%915-412991?logo=openai&logoColor=white)](#)

## Highlights
	•	Results-first: Evolves prompts via targeted edits → scored by a fixed judge → selected for quality × diversity → lessons distilled each round.
	•	Streamed transparency: generate, judge, select, progress, final events over SSE with heartbeats and Last-Event-ID resume.
	•	Operations-ready: Idempotent job creation, cancel semantics, health/metrics endpoints, request IDs, Prometheus text + JSON metrics (sse_clients is a gauge).
	•	Practical defaults: Loopback bind by default; dev bypass only with --dev; bearer-token list for quick setups.

# 60-Second Quickstart

## 0) (optional) Dev ergonomics
pip install -r requirements-dev.txt
pre-commit install

# 1) Run the server (dev mode; loopback bind by default)
python -m innerloop --dev

# 2) Create an optimization job (5 iterations)
curl -s -X POST "http://127.0.0.1:8000/v1/optimize?iterations=5" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_TOKEN}" \  # gitleaks:allow (doc placeholder)
  -d '{
        "prompt": "You are an assistant that writes helpful answers.",
        "target_model_id": "openai/gpt-5-mini",
        "examples": [
          {"input": "Summarize containerization for a CTO", "ideal": "Concise, trade-offs, ops view"}
        ]
      }'

## Stream progress:

curl -N "http://127.0.0.1:8000/v1/optimize/$JOB_ID/events" \
  -H "Authorization: Bearer ${API_TOKEN}"   # gitleaks:allow (doc placeholder)

Event envelope (SSE):

data: {"id":5,"type":"progress","schema_version":1,"job_id":"123e4567","ts":1712345678,"data":{"stage":"select","iteration":2,"best_score":0.71}}

Supports Last-Event-ID resume and periodic :\n\n heartbeats.


# How GEPA Works Here (mental model)

	1.	Propose small, targeted prompt edits 
	2.	Judge with a fixed model for stable, comparable scores + structured feedback.
	3.	Select winners by quality × diversity; distill lessons that guide subsequent edits.
	4.	Repeat for iterations; return the champion prompt + artifacts.

Deep dive: see docs/GEPA.md (workflow, events, practical guidance).

# API Overview

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/optimize` | Start an optimization job |
| GET | `/v1/optimize/{job_id}` | Fetch current job state |
| GET | `/v1/optimize/{job_id}/events` | Stream SSE (`text/event-stream`) |
| GET | `/v1/metrics` | Prometheus text (includes `sse_clients` gauge) |
| GET | `/v1/metricsz` | JSON metrics |
| GET | `/v1/healthz` | Health check |

Auth: set API_BEARER_TOKENS=["token1","token2"] in .env and send Authorization: Bearer <token>.
Dev bypass: allowed only with python -m innerloop --dev or REQUIRE_AUTH=false.

More detail: docs/API.md, docs/SSE.md

# Configuration (essentials)
	•	API_BEARER_TOKENS — JSON list of allowed bearer tokens for dev/test.
	•	JUDGE_MODEL_ID — judge is fixed (not settable via API) to keep scores comparable.
	•	TARGET_MODEL_DEFAULT — default target model; override per request with target_model_id.
	•	HOST (default 127.0.0.1) / PORT (default 8000).
	•	Rate-limit knobs and request size limits are available via env (see docs/ENV.md).

# Production Notes
	•	Judge vs Target: judge is fixed; target model is selectable (target_model_id).
	•	Idempotency: set Idempotency-Key on create to dedupe retries.
	•	Security: loopback bind by default; unauth POST bypass only in --dev; unauth rate-limit buckets are per-client.
	•	Observability: structured logs with request/job IDs; Prom text + JSON metrics; SSE is the source of truth for evolution history.

# Roadmap (beta → stable)
	•	Pluggable judging schemas (task-aware scoring)
	•	Tunable operator sets & evolution knobs
	•	Stronger persistence / artifact replay
	•	Hardened resume & recovery paths

# Learn More
	•	GEPA deep-dive for this service: docs/GEPA.md
	•	API reference & envelopes: docs/API.md, docs/SSE.md
	•	Paper: Guided Evolutionary Prompt Optimization (arXiv:2507.19457)

SEO hints:

Guided evolutionary prompt optimizer, GEPA prompt optimization, GEPA vs GRPO, prompt optimizer service, fixed judge model, streaming SSE prompt evolution.
