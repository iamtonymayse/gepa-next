import importlib

from fastapi.testclient import TestClient


def _mkapp(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["t1","t2"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    return main.app


def test_multiple_bearer_tokens(monkeypatch):
    app = _mkapp(monkeypatch)
    with TestClient(app) as client:
        r = client.post(
            "/v1/optimize",
            json={"prompt": "hi"},
            headers={"Authorization": "Bearer t2"},
        )
    assert r.status_code in (200, 202, 400)
