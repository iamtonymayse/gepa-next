import importlib
import time

from fastapi.testclient import TestClient


def create_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dev")
    monkeypatch.setenv("API_BEARER_TOKENS", '["token"]')
    import innerloop.settings as settings
    importlib.reload(settings)
    import innerloop.main as main
    importlib.reload(main)
    return TestClient(main.app)


def test_admin_endpoints(monkeypatch):
    client = create_client(monkeypatch)
    with client:
        # unauthorized
        assert client.get("/v1/admin/jobs").status_code == 401
        job_id = client.post("/v1/optimize").json()["job_id"]
        # wait for finish
        deadline = time.time() + 2
        while time.time() < deadline:
            state = client.get(f"/v1/optimize/{job_id}").json()
            if state["status"] == "finished":
                break
            time.sleep(0.05)
        resp = client.get("/v1/admin/jobs", headers={"Authorization": "Bearer token"})
        assert resp.status_code == 200
        jobs = resp.json()["jobs"]
        assert any(j["job_id"] == job_id for j in jobs)
        del_resp = client.delete(
            f"/v1/admin/jobs/{job_id}", headers={"Authorization": "Bearer token"}
        )
        assert del_resp.status_code == 204
        state_resp = client.get(f"/v1/optimize/{job_id}")
        assert state_resp.status_code == 404
