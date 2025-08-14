import asyncio

from innerloop.domain import eval as deval
from innerloop.domain import gepa_loop
from innerloop.domain.examples import Example


def test_evaluate_batch_threads_model():
    seen = {"model": None}

    class FakeProv:
        async def complete(self, prompt, model=None):
            seen["model"] = model
            return "ok"

    class Settings:
        TARGET_MODEL_DEFAULT = "default"

    async def main():
        await deval.evaluate_batch(
            FakeProv(),
            "x",
            [Example(id="1", input="q", output="a")],
            Settings,
            model="gpt-4o-mini",
        )

    asyncio.run(main())
    assert seen["model"] == "gpt-4o-mini"


def test_gepa_uses_request_target_model(monkeypatch):
    seen = {"model": None}

    async def fake_evaluate_batch(
        provider, candidate_prompt, examples, settings, model=None
    ):
        seen["model"] = model

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
    monkeypatch.setattr(
        gepa_loop, "update_lessons_journal", lambda lessons, new: lessons
    )
    monkeypatch.setattr(gepa_loop, "apply_edits", lambda c, edits: c)
    monkeypatch.setattr(gepa_loop, "OPERATORS", {"reorder_sections": lambda c, rng: c})
    monkeypatch.setattr(
        gepa_loop, "pareto_filter", lambda items, objectives=None, n=1: list(items)
    )

    async def fake_judge_scores(prompt, candidate, examples, objectives):
        return {"scores": {"overall": 8}}

    monkeypatch.setattr(gepa_loop, "judge_scores", fake_judge_scores)

    async def emit(job, event, data):
        pass

    payload = {
        "prompt": "hi",
        "dataset": {"name": "toy_qa"},
        "budget": {"max_generations": 1},
        "target_model": "mistral-large",
    }

    async def main():
        await gepa_loop.gepa_loop(job=None, emit=emit, payload=payload)

    asyncio.run(main())
    assert seen["model"] == "mistral-large"
