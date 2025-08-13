import importlib, asyncio
from innerloop.domain import engine as eng


def test_provider_singleton(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("USE_MODEL_STUB", "false")
    import innerloop.settings as settings
    importlib.reload(settings)
    importlib.reload(eng)
    p1 = eng.get_provider_from_env()
    p2 = eng.get_provider_from_env()
    assert p1 is p2


def test_provider_close(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("USE_MODEL_STUB", "false")
    import innerloop.settings as settings
    importlib.reload(settings)
    from innerloop.domain import engine as eng
    p = eng.get_provider_from_env()
    assert p is eng.get_provider_from_env()
    asyncio.run(eng.close_provider())
    p2 = eng.get_provider_from_env()
    assert p2 is not p
