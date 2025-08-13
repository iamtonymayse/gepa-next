import importlib
from fastapi.testclient import TestClient


def test_bypass_post_only(monkeypatch):
    """Bypass allows POST /v1/optimize without Authorization but not SSE."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    with TestClient(main.app) as client:
        job_id = client.post("/v1/optimize", json={"prompt": "hi"}).json()["job_id"]
        # SSE without auth must be 401
        resp = client.get(f"/v1/optimize/{job_id}/events")
        assert resp.status_code == 401
        # With auth succeeds
        resp2 = client.get(
            f"/v1/optimize/{job_id}/events", headers={"Authorization": "Bearer token"}
        )
        assert resp2.status_code == 200

