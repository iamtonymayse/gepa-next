import asyncio
import importlib

from innerloop.domain.engine import get_target_provider
from innerloop.domain.eval import evaluate_batch
from innerloop.domain.examples import load_pack
import innerloop.settings as settings


def test_example_pack_and_cache(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    importlib.reload(settings)
    provider = get_target_provider(settings.get_settings())
    pack = load_pack("toy_qa")
    res1 = asyncio.run(
        evaluate_batch(provider, "answer:", pack.examples, settings.get_settings())
    )
    assert set(res1.scores_by_example.keys()) == {"1", "2"}
    res2 = asyncio.run(
        evaluate_batch(provider, "answer:", pack.examples, settings.get_settings())
    )
    assert res2.cached
