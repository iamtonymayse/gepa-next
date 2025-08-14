import asyncio
import importlib


def reload_env(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.domain.engine as engine

    importlib.reload(engine)
    import innerloop.domain.reflection_runner as runner

    importlib.reload(runner)
    return engine, runner


def test_default_local_echo(monkeypatch):
    engine, runner = reload_env(
        monkeypatch, OPENROUTER_API_KEY=None, USE_MODEL_STUB=True
    )
    provider = engine.get_target_provider()
    assert isinstance(provider, engine.LocalEchoProvider)
    result = asyncio.run(runner.run_reflection("hello", "default", 0))
    assert result["proposal"]


def test_stub_false_without_key(monkeypatch):
    engine, runner = reload_env(
        monkeypatch, OPENROUTER_API_KEY=None, USE_MODEL_STUB="false"
    )
    provider = engine.get_target_provider()
    assert isinstance(provider, engine.LocalEchoProvider)
    result = asyncio.run(runner.run_reflection("hi", "default", 0))
    assert result["proposal"]


def test_openrouter_provider(monkeypatch):
    engine, runner = reload_env(
        monkeypatch, OPENROUTER_API_KEY="fake", USE_MODEL_STUB="false"
    )
    provider = engine.get_target_provider()
    assert isinstance(provider, engine.OpenRouterProvider)
    result = asyncio.run(runner.run_reflection("hi", "default", 0))
    assert isinstance(result["proposal"], str)
