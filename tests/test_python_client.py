import importlib
import sys
import pathlib
import asyncio

import httpx
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "clients" / "python"))
from gepa_client import GepaClient, SSEEnvelope  # type: ignore

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def gepa_client(monkeypatch) -> GepaClient:
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    async with main.app.router.lifespan_context(main.app):
        transport = httpx.ASGITransport(app=main.app)
        client = GepaClient("http://test", openrouter_key="dev", bearer_token="token")
        client._client = httpx.AsyncClient(transport=transport, base_url="http://test")
        try:
            yield client
        finally:
            await client.close()


@pytest.mark.anyio
async def test_idempotent(gepa_client: GepaClient):
    j1 = await gepa_client.create_job(
        "hi", idempotency_key="same", examples=[{"input": "x"}]
    )
    j2 = await gepa_client.create_job(
        "hi", idempotency_key="same", examples=[{"input": "x"}]
    )
    assert j1 == j2


@pytest.mark.anyio
async def test_stream_resume(gepa_client: GepaClient):
    job = await gepa_client.create_job("hi", iterations=2, examples=[{"input": "x"}])
    agen = gepa_client.stream(job)
    first = await agen.__anext__()
    assert isinstance(first, SSEEnvelope)
    await agen.aclose()
    events = [env async for env in gepa_client.resume(job)]
    assert events[-1].type in {"finished", "failed", "cancelled"}


@pytest.mark.anyio
async def test_cancel(gepa_client: GepaClient):
    job = await gepa_client.create_job("hi", iterations=2, examples=[{"input": "x"}])
    cancel_task = asyncio.create_task(gepa_client.cancel(job))
    events = []
    async for env in gepa_client.stream(job):
        events.append(env.type)
        if env.type in {"cancelled", "finished", "failed"}:
            break
    await cancel_task
    assert "cancelled" in events
