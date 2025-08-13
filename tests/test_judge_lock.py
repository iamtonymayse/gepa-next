import importlib, asyncio
from fastapi.testclient import TestClient
from innerloop.api.jobs.store import MemoryJobStore


def test_judge_is_locked(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("USE_MODEL_STUB", "true")
    import innerloop.settings as settings; importlib.reload(settings)
    import innerloop.domain.judge as judge; importlib.reload(judge)
    store = MemoryJobStore()
    before = judge.CALLS
    assert settings.get_settings().JUDGE_MODEL_ID.startswith("openai:")

    async def go():
        await judge.judge_pair("task", "A", "B", store=store)
        await judge.judge_pair("task", "A", "B", store=store)

    asyncio.run(go())
    after = judge.CALLS
    assert after == before + 1
