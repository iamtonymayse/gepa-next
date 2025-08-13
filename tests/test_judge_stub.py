import importlib
import asyncio

from innerloop.domain.judge import get_judge
import innerloop.settings as settings


def test_judge_stub_ranking(monkeypatch):
    monkeypatch.setenv("USE_JUDGE_STUB", "true")
    importlib.reload(settings)
    s = settings.get_settings()
    judge = get_judge(s)
    proposals = ["short good", "much longer proposal with many many words", "mid"]
    ranked = asyncio.run(judge.rank(prompt="p", proposals=proposals, rubric=None))
    items = [p for p, _ in ranked]
    assert set(items) == set(proposals)
    assert items[0] in {"short good", "mid"}

