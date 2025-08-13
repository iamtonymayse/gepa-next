import importlib


def test_judge_cache(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    import innerloop.domain.judge as judge
    importlib.reload(judge)
    import asyncio

    async def go():
        before = judge.CALLS
        a, b, task = "A", "B", "task"
        await judge.judge_pair(a, b, task)
        await judge.judge_pair(a, b, task)
        after = judge.CALLS
        assert after == before + 1

    asyncio.run(go())
