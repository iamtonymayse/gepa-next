import importlib
from fastapi.testclient import TestClient


def test_prometheus_metrics_expose_http_and_sse(monkeypatch):
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        r = client.get("/v1/healthz")
        assert r.status_code == 200
        m = client.get("/v1/metrics")
        assert m.status_code == 200
        text = m.text
        assert "http_requests_total" in text
        assert 'path="/v1/healthz"' in text
        assert "sse_clients" in text

