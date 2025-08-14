import importlib

from fastapi.testclient import TestClient


def _mkapp(monkeypatch):
    """Create app with minimal auth so middleware passes."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings

    importlib.reload(settings)
    import innerloop.main as main

    importlib.reload(main)
    return main.app


def test_cancel_returns_cancelled_status(monkeypatch):
    app = _mkapp(monkeypatch)
    client = TestClient(app)
    with client:
        resp = client.post(
            "/v1/optimize",
            json={"prompt": "hi"},
            headers={"Authorization": "Bearer token"},
            params={"iterations": 5},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        got = client.delete(
            f"/v1/optimize/{job_id}", headers={"Authorization": "Bearer token"}
        )
        assert got.status_code == 200
        body = got.json()
        assert body.get("status") == "cancelled"
