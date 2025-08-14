import asyncio
import importlib

from innerloop.api.jobs.store import MemoryJobStore


def test_judge_cache(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    import innerloop.domain.judge as judge

    importlib.reload(judge)
    store = MemoryJobStore()

    async def go():
        before = judge.CALLS
        await judge.judge_pair("task", "A", "B", store=store)
        await judge.judge_pair("task", "A", "B", store=store)
        after = judge.CALLS
        assert after == before + 1

    asyncio.run(go())
