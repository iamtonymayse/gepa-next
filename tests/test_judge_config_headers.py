import importlib


def reload_engine(monkeypatch):
    monkeypatch.setenv("USE_MODEL_STUB", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.domain.engine as engine

    importlib.reload(engine)
    return engine


def test_judge_headers(monkeypatch):
    engine = reload_engine(monkeypatch)
    provider = engine.get_judge_provider()
    assert isinstance(provider, engine.OpenRouterProvider)
    assert provider.client.headers.get("X-OpenAI-Api-Key") == "y"
