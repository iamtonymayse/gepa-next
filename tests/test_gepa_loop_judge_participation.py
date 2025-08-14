import asyncio

from innerloop.domain import gepa_loop


def test_gepa_includes_judge_axis(monkeypatch):
    called = {"judge": 0}

    async def fake_judge_scores(prompt, candidate, examples, objectives):
        called["judge"] += 1
        return {"scores": {"overall": 8}}

    monkeypatch.setattr(gepa_loop, "judge_scores", fake_judge_scores)

    async def fake_evaluate_batch(provider, candidate_prompt, examples, settings, model=None):
        class Res:
            mean_scores = {"exact_match": 1.0}
            cost = 0.0
            latency = 0.0
            traces = []

        return Res()

    monkeypatch.setattr(gepa_loop, "evaluate_batch", fake_evaluate_batch)

    async def fake_run_reflection(*args, **kwargs):
        return {}

    monkeypatch.setattr(gepa_loop, "run_reflection", fake_run_reflection)
    monkeypatch.setattr(gepa_loop, "update_lessons_journal", lambda lessons, new: lessons)
    monkeypatch.setattr(gepa_loop, "apply_edits", lambda c, edits: c)
    monkeypatch.setattr(gepa_loop, "OPERATORS", {"reorder_sections": lambda c, rng: c})

    captured = {}

    def fake_pareto_filter(items, objectives=None, n=1):
        captured["candidates"] = list(items)
        return list(items)

    monkeypatch.setattr(gepa_loop, "pareto_filter", fake_pareto_filter)

    async def emit(job, event, data):
        pass

    payload = {"prompt": "hello", "dataset": {"name": "toy_qa"}, "budget": {"max_generations": 1}}

    async def main():
        await gepa_loop.gepa_loop(job=None, emit=emit, payload=payload)

    asyncio.run(main())

    assert called["judge"] > 0
    assert any("judge_score" in c.meta for c in captured.get("candidates", []))

