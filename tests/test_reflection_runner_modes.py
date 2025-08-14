import asyncio
import importlib


def test_run_reflection_modes_stub(monkeypatch):
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    import innerloop.domain.reflection_runner as rr

    importlib.reload(rr)
    base = "Prompt base"
    ex = [{"input": "foo", "expected": "bar"}]
    for i, mode in enumerate(["author", "reviewer", "planner", "revision"]):
        res = asyncio.run(
            rr.run_reflection(
                base, mode, i, examples=ex, target_model="openai:gpt-4o-mini"
            )
        )
        assert res["mode"] == mode
        assert isinstance(res["lessons"], list) and res["lessons"]
        assert isinstance(res["edits"], list)
