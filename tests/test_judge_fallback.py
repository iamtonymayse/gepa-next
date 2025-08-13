import pytest

from innerloop.api import metrics
from innerloop.domain import engine as engine_mod
from innerloop.domain import judge as judge_mod


class _FailingProvider:
    async def complete(self, *args, **kwargs):
        raise RuntimeError("provider down")


class _BadJsonProvider:
    async def complete(self, *args, **kwargs):
        return "not-json"


@pytest.mark.asyncio
async def test_judge_fallback_on_provider_error(monkeypatch):
    monkeypatch.setattr(engine_mod, "get_judge_provider", lambda *a, **k: _FailingProvider())
    start = metrics.snapshot_metrics_json().get("judge_failures", 0)
    res = await judge_mod.judge(task="t", a="short", b="longer content")
    assert res["winner"] in {"A", "B"}
    assert res["justification"] == "fallback"
    end = metrics.snapshot_metrics_json().get("judge_failures", 0)
    assert end == start + 1


@pytest.mark.asyncio
async def test_judge_fallback_on_invalid_json(monkeypatch):
    monkeypatch.setattr(engine_mod, "get_judge_provider", lambda *a, **k: _BadJsonProvider())
    start = metrics.snapshot_metrics_json().get("judge_failures", 0)
    res = await judge_mod.judge(task="t", a="short", b="much longer text than a")
    assert res["winner"] in {"A", "B"}
    assert res["justification"] == "fallback"
    end = metrics.snapshot_metrics_json().get("judge_failures", 0)
    assert end == start + 1
