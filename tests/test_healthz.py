import importlib

from fastapi.testclient import TestClient


def test_healthz(monkeypatch):
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
