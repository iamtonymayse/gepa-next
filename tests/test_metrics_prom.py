import importlib
from fastapi.testclient import TestClient


def test_metrics_snapshot(monkeypatch):
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        r = client.get("/v1/healthz")
        assert r.status_code == 200
        m = client.get("/v1/metricsz")
        assert m.status_code == 200
        data = m.json()
        assert "jobs_created" in data
        assert "histograms" in data
