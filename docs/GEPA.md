# GEPA in gepa-next

This document explains how GEPA (Guided Evolutionary Prompt Optimization) is realized in this codebase and how to use it effectively.

> Summary: We evolve prompts in small steps, score them with a fixed judge, keep what’s great and diverse, record lessons, and iterate. The paper (arXiv:2507.19457) reports that this approach outperforms GRPO-style baselines in their tests; this service packages that workflow behind a stable API.

---

## Core ideas (GEPA → implementation)

| GEPA Concept | Why it matters | Where it lives here |
| --- | --- | --- |
| Fixed judge model | Comparable, stable scoring across generations | Config `JUDGE_MODEL_ID` (code-enforced); never set via API |
| Target model | The model we’re actually optimizing prompts for | Request field `target_model_id` (or `target_model`) |
| Population evolution | Explore multiple small edits per generation | Evolution step in job loop; emits generate/select events |
| Selection (quality × diversity) | Avoids converging to brittle prompts | Selection step; top candidates and pareto-like filtering |
| Lessons journal | Cumulative knowledge to guide later edits | Logged in job state and surfaced via events |
| Deterministic judge pass | Reduces noise vs. reward-model drift | Judge fixed; scoring prompt kept stable across run |

> Note: Names/fields above mirror code and API; see docs/API.md for the JSON shapes and docs/SSE.md for event envelopes.

---

## The optimization loop

Pseudocode of the server’s evolution pass:

```text
for iteration in 1..N:
  1) Propose
  candidates := mutate(base_prompt, lessons, examples)
      operators: add clarifying instruction, tighten constraints,
                 restructure steps, condition on examples, tweak style/voice.

  2) Evaluate (fixed judge)
  scored := [
    {prompt: p, score: judge(p, examples), feedback: f}
    for p in candidates
  ]

  3) Select
  best, survivors := select(scored, keep_diversity=True)
  lessons += distill_feedback(survivors)
  base_prompt := best.prompt

  4) Emit events
  sse(progress: {iteration, best_score, lesson_count})
```

Events (SSE) you’ll see:
- `generate` — new candidate prompts proposed
- `judge` — scoring/feedback from the fixed judge
- `select` — winners chosen; lessons distilled
- `progress` — iteration checkpoint with best score
- `final` — champion prompt and artifacts

All events use this envelope (see docs/SSE.md):

```
{"id":5,"type":"progress","schema_version":1,"job_id":"123e4567","ts":1712345678,"data":{...}}
```

---

## Using the API for GEPA workflows

### Create a job
```bash
curl -s -X POST "http://127.0.0.1:8000/v1/optimize?iterations=6" \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-001" \
  -d '{
        "prompt": "You are a precise, helpful technical writer.",
        "target_model_id": "openai/gpt-5-mini",
        "examples": [
          {"input": "Summarize containerization for CTO", "ideal": "Concise, trade-offs, ops view"},
          {"input": "Explain vector DB pros/cons to PM", "ideal": "Non-hype, risks, budgets"}
        ]
      }'
```

### Stream progress (SSE)
```bash
curl -N "http://127.0.0.1:8000/v1/optimize/$JOB_ID/events" \
  -H "Authorization: Bearer dev-token"
```
- Heartbeats (`:\n\n`) keep the connection warm.
- Resume with `Last-Event-ID: ` to skip what you’ve already processed.

### Get the result
```bash
curl -s "http://127.0.0.1:8000/v1/optimize/$JOB_ID" \
  -H "Authorization: Bearer dev-token" | jq .
```
Response includes the champion prompt, a sketch of lessons, and basic scoring.

---

## Practical guidance

- Seed with real examples. GEPA shines when the judge can compare outputs to concrete ideals. Provide 2–10 bite-sized examples that reflect your domain.
- Constrain, don’t bloat. The best edits tighten intent and structure; avoid adding encyclopedic boilerplate.
- Prefer more iterations over huge populations. A few tight generations usually beat a single massive one.
- Lock the judge. Changing the judge mid-run invalidates comparability; this service prevents that.
- Use idempotency. Set `Idempotency-Key` per run to avoid duplicate jobs in retries.

---

## How this differs from GRPO-style loops
- Fixed judge vs. evolving reward: Reduces reward drift; makes scores comparable across generations.
- Lesson journal: Persisted synthesis of what helped/hurt, guiding later mutations.
- Diversity-aware selection: Keeps multiple promising directions alive to avoid premature convergence.

As reported by the GEPA paper, these ingredients together outperformed GRPO baselines on their benchmarks. Your mileage will vary by task; the service exposes the same levers so you can reproduce or adapt these dynamics.

---

## Artifacts & observability
- `/v1/metrics` (Prom text) and `/v1/metricsz` (JSON) include basic counters and `sse_clients`.
- Logs include request IDs and job IDs for traceability.
- The SSE stream is the source of truth for what happened during evolution; consider capturing it for audits.

---

## Appendix: Field reference
- Body (POST /v1/optimize)
  - `prompt` (string, required) — initial prompt to evolve.
  - `target_model_id` (string, recommended) — model we’re optimizing for.
  - `examples` (array, optional) — [{ "input": "...", "ideal": "..." }].
  - `config` (object, optional) — evolution knobs (if exposed in this build).
- Headers
  - `Authorization: Bearer <token>` — required unless running with `--dev`.
  - `Idempotency-Key: <opaque>` — dedupe protection for create.
- SSE
  - `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
  - `Last-Event-ID` supported for resume.
