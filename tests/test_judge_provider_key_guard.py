from types import SimpleNamespace

import pytest

from innerloop.domain import engine as eng


def test_openrouter_guard_raises_without_openai_key(monkeypatch):
    monkeypatch.setattr(eng, "_judge_provider_singleton", None, raising=False)
    settings = SimpleNamespace(
        USE_MODEL_STUB=False,
        JUDGE_PROVIDER="openrouter",
        OPENROUTER_API_KEY="ok",
        OPENAI_API_KEY=None,
        ALLOW_JUDGE_FALLBACK=False,
        JUDGE_TIMEOUT_S=5,
    )
    with pytest.raises(RuntimeError):
        eng.get_judge_provider(settings)


def test_openrouter_fallback_when_allowed(monkeypatch):
    monkeypatch.setattr(eng, "_judge_provider_singleton", None, raising=False)
    settings = SimpleNamespace(
        USE_MODEL_STUB=False,
        JUDGE_PROVIDER="openrouter",
        OPENROUTER_API_KEY="ok",
        OPENAI_API_KEY=None,
        ALLOW_JUDGE_FALLBACK=True,
        JUDGE_TIMEOUT_S=5,
    )
    prov = eng.get_judge_provider(settings)
    assert prov.__class__.__name__ in {"LocalEchoProvider", "OpenAIProvider"}
