import importlib

from fastapi.testclient import TestClient


def _mkapp(monkeypatch, require_auth: bool):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    monkeypatch.setenv("REQUIRE_AUTH", "true" if require_auth else "false")
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    return main.app


def test_post_optimize_requires_auth_in_prod_mode(monkeypatch):
    app = _mkapp(monkeypatch, require_auth=True)
    with TestClient(app) as client:
        r = client.post("/v1/optimize", json={"prompt": "hi"})
    assert r.status_code in (401, 403)


def test_post_optimize_allowed_in_dev_mode(monkeypatch):
    app = _mkapp(monkeypatch, require_auth=False)
    with TestClient(app) as client:
        r = client.post("/v1/optimize", json={"prompt": "hi"})
    assert r.status_code in (200, 202, 400)
