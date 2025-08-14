import asyncio
from types import SimpleNamespace

from innerloop.domain import gepa_loop


def test_gepa_emits_selected(monkeypatch):
    events: list[tuple[str, dict]] = []

    async def fake_emit(job, name, payload):
        events.append((name, payload))

    async def fake_evaluate_batch(provider, prompt, examples, settings, model=None):
        class Res:
            mean_scores = {"exact_match": 0.0}
            cost = 0.0
            latency = 0.0

        return Res()

    async def fake_judge_scores(prompt, candidate, examples, objectives):
        return {"scores": {}}

    async def fake_run_reflection(*args, **kwargs):
        return {}

    monkeypatch.setattr(gepa_loop, "evaluate_batch", fake_evaluate_batch)
    monkeypatch.setattr(gepa_loop, "judge_scores", fake_judge_scores)
    monkeypatch.setattr(gepa_loop, "run_reflection", fake_run_reflection)
    monkeypatch.setattr(gepa_loop, "apply_edits", lambda cand, edits: cand)
    monkeypatch.setattr(gepa_loop, "OPERATORS", {"reorder_sections": lambda c, rng=None: c})
    monkeypatch.setattr(gepa_loop, "load_pack", lambda name: SimpleNamespace(examples=[]))
    monkeypatch.setattr(gepa_loop, "get_target_provider", lambda settings: None)

    payload = {
        "prompt": "p",
        "dataset": {"name": "toy_qa"},
        "budget": {"max_generations": 1},
    }
    asyncio.run(gepa_loop.gepa_loop("job", fake_emit, payload))

    sel_payloads = [p for n, p in events if n == "selected"]
    assert sel_payloads
    meta = sel_payloads[0]["meta"]
    assert "judge_score" in meta and "diversity" in meta and "score" in meta
