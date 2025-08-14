import importlib

import pytest

from innerloop.api import metrics
from innerloop.domain import judge as dj
import innerloop.settings as settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class BadJsonProvider:
    async def complete(self, *args, **kwargs):
        return "not-json"


async def test_judge_scores_increments_metric_on_bad_json(monkeypatch):
    monkeypatch.setenv("USE_MODEL_STUB", "false")
    importlib.reload(settings)
    monkeypatch.setattr(dj, "get_judge_provider", lambda s: BadJsonProvider())
    start = metrics.snapshot_metrics_json().get("judge_failures", 0)
    out = await dj.judge_scores(
        prompt="p", candidate="c", examples=None, objectives=["brevity"]
    )
    end = metrics.snapshot_metrics_json().get("judge_failures", 0)
    assert end == start + 1
    assert out.get("unavailable") is True
    assert out["scores"] == {}
