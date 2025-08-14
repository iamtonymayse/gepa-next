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


def test_healthz_v1(monkeypatch):
    monkeypatch.delenv("API_BEARER_TOKENS", raising=False)
    import importlib

    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        resp_root = client.get("/healthz")
        resp_v1 = client.get("/v1/healthz")
    assert resp_v1.status_code == 200
    assert resp_root.json() == resp_v1.json()
