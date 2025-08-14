import importlib

from innerloop.domain import judge as judge_mod


def test_get_judge_returns_llm_when_not_stub(monkeypatch):
    """Factory returns JudgeLLM when stubs are disabled."""
    # Force non-stub provider selection but don’t actually call the network.
    monkeypatch.setenv("USE_JUDGE_STUB", "false")
    monkeypatch.setenv("USE_MODEL_STUB", "false")
    monkeypatch.setenv("JUDGE_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "ok")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    # Reload modules so new env vars are picked up.
    import innerloop.settings as settings

    importlib.reload(settings)
    importlib.reload(judge_mod)

    j = judge_mod.get_judge(settings.get_settings())
    # Type check only; avoid any calls that would trigger I/O.
    assert isinstance(j, judge_mod.JudgeLLM)
