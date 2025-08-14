import pytest

from innerloop.api import metrics
from innerloop.domain import judge as judge_mod

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class _FailingProvider:
    async def complete(self, *args, **kwargs):
        raise RuntimeError("provider down")


class _BadJsonProvider:
    async def complete(self, *args, **kwargs):
        return "not-json"


async def test_judge_fallback_on_provider_error(monkeypatch):
    monkeypatch.setattr(judge_mod, "get_judge_provider", lambda *a, **k: _FailingProvider())
    start = metrics.snapshot_metrics_json().get("judge_failures", 0)
    res = await judge_mod.judge(task="t", a="short", b="longer content")
    assert res["winner"] in {"A", "B"}
    assert res["justification"] == "fallback"
    end = metrics.snapshot_metrics_json().get("judge_failures", 0)
    assert end == start + 1


async def test_judge_fallback_on_invalid_json(monkeypatch):
    monkeypatch.setattr(judge_mod, "get_judge_provider", lambda *a, **k: _BadJsonProvider())
    start = metrics.snapshot_metrics_json().get("judge_failures", 0)
    res = await judge_mod.judge(task="t", a="short", b="much longer text than a")
    assert res["winner"] in {"A", "B"}
    assert res["justification"] == "fallback"
    end = metrics.snapshot_metrics_json().get("judge_failures", 0)
    assert end == start + 1
