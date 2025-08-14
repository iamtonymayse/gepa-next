import importlib

from fastapi.testclient import TestClient


def _mkapp(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    return main.app


def test_metrics_types(monkeypatch):
    app = _mkapp(monkeypatch)
    with TestClient(app) as client:
        r = client.get("/v1/metrics")
    assert r.status_code == 200
    text = r.text
    assert "# TYPE sse_clients gauge" in text
