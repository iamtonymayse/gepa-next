import asyncio
import importlib

from innerloop.domain import judge as dj


def test_judge_pair_is_deterministic(monkeypatch):
    calls = []

    class P:
        SUPPORTED_KWARGS = ("seed",)

        async def complete(self, **kw):
            calls.append(kw)
            return '{"winner": "A"}'

    # ensure we don't use the internal model stub path
    monkeypatch.setenv("USE_MODEL_STUB", "false")
    import innerloop.settings as settings

    importlib.reload(settings)

    monkeypatch.setattr(dj, "get_judge_provider", lambda s: P())

    out1 = asyncio.run(dj.judge_pair("t", "A", "B"))
    out2 = asyncio.run(dj.judge_pair("t", "A", "B"))

    assert out1 == out2
    assert calls[0]["temperature"] == 0.0
    assert calls[0]["max_tokens"] == 64
    assert "seed" in calls[0]
